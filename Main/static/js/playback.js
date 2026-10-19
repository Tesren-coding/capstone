import {CanvasViewport, stationProcesses, stationTotals} from "./canvas-tools.js";
import {drawBox, drawStation, drawPart, drawOperator, drawOperatorTracer, drawBanner, drawLegend} from "./draw.js";
import {buildPositionsFromScenario} from "./positions.js";
import {buildOperatorState, updateOperators} from "./state.js";
import {requestJson} from "./api.js";
import {visitedLocationsForOperator, operatorAtLegendPoint, sortOperatorIds} from "./operator-highlight.js";
import {startingSwipMetrics} from "./simulation-metrics.js";

// playback.js — Simulation playback, controls and tooltips.
// ============================================================
// PART 1 — Setup variables
// ============================================================
const canvas     = document.getElementById("sim-canvas");
const ctx        = canvas.getContext("2d");
const statusText = document.getElementById("status-text");
const metricsSection = document.getElementById('simulation-metrics');
const swipTotalValue = document.getElementById('swip-total-value');
const startingSwipValue = document.getElementById('metric-starting-swip');
const pieLegend = document.getElementById('swip-pie-legend');
const pieSlices = document.getElementById('swip-pie-slices');
const pieChart = document.getElementById('swip-pie-chart');
const pieFigure = document.querySelector('.swip-pie-figure');
const pieCenter = document.getElementById('swip-pie-center');
const pieHoverPointer = document.getElementById('swip-pie-hover-pointer');
const pieHoverLine = document.getElementById('swip-hover-line');
const pieHoverDot = document.getElementById('swip-hover-dot');
const pieTooltip = document.getElementById('swip-pie-tooltip');
const pieTooltipTitle = document.getElementById('swip-tooltip-title');
const pieTooltipDetail = document.getElementById('swip-tooltip-detail');
const pieTooltipExtra = document.getElementById('swip-tooltip-extra');
let focusedSwipSegment = null;
let swipSliceNodes = new Map();
let currentSwip = null;

function polarPoint(cx, cy, radius, angleRadians) {
    return { x: cx + radius * Math.cos(angleRadians), y: cy + radius * Math.sin(angleRadians) };
}
function buildSlicePath(cx, cy, outerRadius, innerRadius, startAngle, endAngle) {
    const span = endAngle - startAngle;
    // SVG cannot draw a complete circle using one arc whose endpoints coincide.
    // Split a single-category 100% donut slice into two semicircular arcs.
    const fullCircle = span >= Math.PI * 2 - 1e-7;
    const largeArcFlag = span > Math.PI ? 1 : 0;
    const outerStart = polarPoint(cx, cy, outerRadius, startAngle);
    const outerEnd = polarPoint(cx, cy, outerRadius, endAngle);
    const innerEnd = polarPoint(cx, cy, innerRadius, endAngle);
    const innerStart = polarPoint(cx, cy, innerRadius, startAngle);
    if (fullCircle) {
        const outerMiddle = polarPoint(cx, cy, outerRadius, startAngle + Math.PI);
        const innerMiddle = polarPoint(cx, cy, innerRadius, startAngle + Math.PI);
        return [
            `M ${outerStart.x} ${outerStart.y}`,
            `A ${outerRadius} ${outerRadius} 0 0 1 ${outerMiddle.x} ${outerMiddle.y}`,
            `A ${outerRadius} ${outerRadius} 0 0 1 ${outerEnd.x} ${outerEnd.y}`,
            `L ${innerEnd.x} ${innerEnd.y}`,
            `A ${innerRadius} ${innerRadius} 0 0 0 ${innerMiddle.x} ${innerMiddle.y}`,
            `A ${innerRadius} ${innerRadius} 0 0 0 ${innerStart.x} ${innerStart.y}`,
            'Z',
        ].join(' ');
    }
    return [
        `M ${outerStart.x} ${outerStart.y}`,
        `A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 1 ${outerEnd.x} ${outerEnd.y}`,
        `L ${innerEnd.x} ${innerEnd.y}`,
        `A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 0 ${innerStart.x} ${innerStart.y}`,
        'Z',
    ].join(' ');
}

function hideSwipHover() {
    focusedSwipSegment = null;
    pieTooltip.hidden = true;
    pieHoverPointer.setAttribute('visibility', 'hidden');
    for (const path of swipSliceNodes.values()) {
        path.classList.remove('is-hovered', 'is-muted');
        path.removeAttribute('transform');
    }
    for (const legendItem of pieLegend.children) {
        legendItem.classList.remove('is-hovered', 'is-muted');
    }
}

function showSwipHover(key) {
    if (!currentSwip) return;
    const total = currentSwip.totalSwip;
    const category = currentSwip.categories.find(item => item.key === key);
    if (key !== 'total' && (!category || category.value <= 0)) return;
    focusedSwipSegment = key;
    const percent = category && total > 0 ? (category.value / total * 100).toFixed(1) : '100.0';
    const boxes = currentSwip.swipBoxes;
    const occupied = currentSwip.swipBoxesWithParts;
    pieTooltipTitle.textContent = key === 'total' ? 'Total starting SWIP' : category.label;
    pieTooltipDetail.textContent = key === 'total'
        ? `${total} starting parts across all categories`
        : `${category.value} ${category.value === 1 ? 'part' : 'parts'} · ${percent}% of total`;
    // Box occupancy is relevant only to the SWIP box category, not to
    // IN boxes, station parts, or the total in the donut center.
    pieTooltipExtra.hidden = key !== 'swipBoxes';
    pieTooltipExtra.textContent = key === 'swipBoxes'
        ? `SWIP boxes starting with parts: ${occupied} of ${boxes}`
        : '';
    pieTooltip.hidden = false;
    pieHoverPointer.setAttribute('visibility', key === 'total' ? 'hidden' : 'visible');

    let anchorX = 160;
    let anchorY = 110;
    for (const [segmentKey, path] of swipSliceNodes) {
        const isActive = segmentKey === key;
        path.classList.toggle('is-hovered', isActive);
        path.classList.toggle('is-muted', key !== 'total' && !isActive);
        if (isActive) {
            const angle = Number(path.dataset.midAngle);
            const displacement = polarPoint(0, 0, 7, angle);
            path.setAttribute('transform', `translate(${displacement.x} ${displacement.y})`);
            const lineStart = polarPoint(160, 160, 124, angle);
            const lineEnd = polarPoint(160, 160, 151, angle);
            pieHoverLine.setAttribute('x1', lineStart.x);
            pieHoverLine.setAttribute('y1', lineStart.y);
            pieHoverLine.setAttribute('x2', lineEnd.x);
            pieHoverLine.setAttribute('y2', lineEnd.y);
            pieHoverDot.setAttribute('cx', lineEnd.x);
            pieHoverDot.setAttribute('cy', lineEnd.y);
            anchorX = lineEnd.x;
            anchorY = lineEnd.y;
        } else {
            path.removeAttribute('transform');
        }
    }
    for (const legendItem of pieLegend.children) {
        const isActive = legendItem.dataset.key === key;
        legendItem.classList.toggle('is-hovered', isActive);
        legendItem.classList.toggle('is-muted', key !== 'total' && !isActive);
    }
    const rect = pieChart.getBoundingClientRect();
    const figureRect = pieFigure.getBoundingClientRect();
    // Place the callout alongside the highlighted sector. Clamp to the chart
    // width so it remains readable when a segment is near either edge.
    const x = rect.left - figureRect.left + rect.width * anchorX / 320;
    const y = rect.top - figureRect.top + rect.height * anchorY / 320;
    const width = Math.min(232, pieFigure.clientWidth - 12);
    const left = Math.max(6, Math.min(x - width / 2, pieFigure.clientWidth - width - 6));
    const top = Math.max(5, Math.min(y - 104, pieFigure.clientHeight - 116));
    pieTooltip.style.width = `${width}px`;
    pieTooltip.style.left = `${left}px`;
    pieTooltip.style.top = `${top}px`;
}

function renderStartingSwipChart() {
    const m = startingSwipMetrics(scenario);
    currentSwip = m;
    swipTotalValue.textContent = m.totalSwip;
    startingSwipValue.textContent = m.totalSwip;
    hideSwipHover();
    swipSliceNodes = new Map();
    pieLegend.replaceChildren();
    pieSlices.replaceChildren();

    const total = m.totalSwip;
    const slices = m.categories.filter(item => item.value > 0);
    if (total <= 0) {
        const emptyCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        emptyCircle.setAttribute('cx', '160');
        emptyCircle.setAttribute('cy', '160');
        emptyCircle.setAttribute('r', '118');
        emptyCircle.setAttribute('fill', '#eef3f8');
        pieSlices.append(emptyCircle);
    } else {
        let startAngle = -Math.PI / 2;
        for (const item of slices) {
            const angle = (item.value / total) * Math.PI * 2;
            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('d', buildSlicePath(160, 160, 118, 86, startAngle, startAngle + angle));
            path.setAttribute('fill', item.color);
            path.setAttribute('stroke', '#ffffff');
            path.setAttribute('stroke-width', '2');
            path.setAttribute('tabindex', '0');
            path.setAttribute('role', 'button');
            path.setAttribute('aria-label', `${item.label}: ${item.value} parts, ${(item.value / total * 100).toFixed(1)} percent`);
            path.classList.add('swip-pie-slice');
            path.dataset.key = item.key;
            path.dataset.midAngle = startAngle + angle / 2;
            path.addEventListener('mouseenter', () => showSwipHover(item.key));
            path.addEventListener('focus', () => showSwipHover(item.key));
            path.addEventListener('mouseleave', () => hideSwipHover());
            path.addEventListener('blur', () => hideSwipHover());
            swipSliceNodes.set(item.key, path);
            pieSlices.append(path);
            startAngle += angle;
        }
    }

    for (const item of m.categories) {
        const percentage = total > 0 ? ((item.value / total) * 100).toFixed(1) : '0.0';
        const row = document.createElement('div');
        row.className = 'swip-legend-item';
        row.dataset.key = item.key;
        row.innerHTML = `
            <span class="swip-legend-swatch" style="background:${item.color};"></span>
            <span class="swip-legend-text"><strong>${item.label}</strong><span>${percentage}% of total SWIP</span></span>
            <span class="swip-legend-value">${item.value}</span>`;
        if (item.value > 0) {
            row.tabIndex = 0;
            row.addEventListener('mouseenter', () => showSwipHover(item.key));
            row.addEventListener('mouseleave', () => hideSwipHover());
            row.addEventListener('focus', () => showSwipHover(item.key));
            row.addEventListener('blur', () => hideSwipHover());
        }
        pieLegend.append(row);
    }
    metricsSection.hidden = false;
}

pieCenter.addEventListener('mouseenter', () => showSwipHover('total'));
pieCenter.addEventListener('mouseleave', hideSwipHover);
pieCenter.addEventListener('focus', () => showSwipHover('total'));
pieCenter.addEventListener('blur', hideSwipHover);

const view = new CanvasViewport(canvas, document.getElementById('canvas-controls'), () => {
    hoverPointer = null;
    tooltip.hidden = true;
});
const tooltip = document.getElementById('station-tooltip');
let hoverPointer = null;
let hoveredCanvasOperator = null;
let hoveredChipOperator = null;
let pinnedOperator = null;
let highlightedLocations = new Set();
const highlightLegend = document.getElementById('operator-highlight-legend');
const clearHighlightButton = document.getElementById('clear-operator-highlight');
function activeHighlightOperator() {
    const id = hoveredChipOperator ?? hoveredCanvasOperator ?? pinnedOperator;
    return id && scenario?.operators?.[id] ? id : null;
}
function refreshHighlightUI() {
    const focused = activeHighlightOperator();
    highlightedLocations = focused ? visitedLocationsForOperator(scenario.operators[focused], scenario) : new Set();
    clearHighlightButton.disabled = pinnedOperator === null;
    for (const button of highlightLegend.querySelectorAll('[data-operator-id]')) {
        const id = button.dataset.operatorId;
        button.setAttribute('aria-pressed', String(pinnedOperator === id));
        button.style.outline = focused === id ? '2px solid #1e3c78' : '';
        button.style.opacity = focused && focused !== id ? '0.45' : '1';
    }
}
function populateHighlightLegend() {
    highlightLegend.replaceChildren();
    for (const id of opNames) {
        const operator = scenario.operators[id];
        const button = document.createElement('button');
        button.type = 'button';
        button.dataset.operatorId = id;
        button.setAttribute('aria-label', `Highlight ${id}'s work area`);
        button.setAttribute('aria-pressed', 'false');
        button.style.cssText = 'display:inline-flex;align-items:center;gap:6px;padding:7px 11px;background:#fff;border:1px solid #9cacc1;border-radius:18px;cursor:pointer;font-size:13px;';
        const swatch = document.createElement('span');
        swatch.style.cssText = `display:inline-block;width:12px;height:12px;border-radius:50%;background:${Array.isArray(operator.color) ? `rgb(${operator.color.join(',')})` : operator.color || '#888'};`;
        button.append(swatch, document.createTextNode(id));
        button.addEventListener('mouseenter', () => {hoveredChipOperator = id; refreshHighlightUI();});
        button.addEventListener('mouseleave', () => {if (hoveredChipOperator === id) hoveredChipOperator = null; refreshHighlightUI();});
        button.addEventListener('focus', () => {hoveredChipOperator = id; refreshHighlightUI();});
        button.addEventListener('blur', () => {if (hoveredChipOperator === id) hoveredChipOperator = null; refreshHighlightUI();});
        button.addEventListener('click', () => {pinnedOperator = pinnedOperator === id ? null : id; refreshHighlightUI();});
        highlightLegend.append(button);
    }
    refreshHighlightUI();
}
clearHighlightButton.addEventListener('click', () => {pinnedOperator = null; hoveredChipOperator = null; hoveredCanvasOperator = null; refreshHighlightUI();});
canvas.addEventListener('mousemove', e => {
    hoverPointer = { clientX: e.clientX, clientY: e.clientY };
    const id = operatorAtLegendPoint(view.pixelPoint(e), opNames, canvas.height);
    if (id !== hoveredCanvasOperator) {hoveredCanvasOperator = id; refreshHighlightUI();}
    canvas.style.cursor = id ? 'pointer' : '';
    updateStationTooltip();
});
canvas.addEventListener('mouseleave', () => { hoverPointer = null; hoveredCanvasOperator = null; canvas.style.cursor = ''; tooltip.hidden = true; refreshHighlightUI(); });
window.addEventListener('scroll', () => { hoverPointer = null; tooltip.hidden = true; }, true);

function updateStationTooltip() {
    if (!hoverPointer || !scenario || !opState || view.isPanning || hoveredCanvasOperator) { tooltip.hidden = true; return; }
    const p = view.worldPoint(hoverPointer);
    const entry = Object.entries(scenario.stations).reverse().find(([, s]) =>
        p.x >= s.x && p.x <= s.x + s.w && p.y >= s.y && p.y <= s.y + s.h);
    if (!entry) { tooltip.hidden = true; return; }
    const [sid, s] = entry;
    const machine = opState.stationState[sid];
    const totals = stationTotals(s);
    const lines = [`Station S${sid}`, `Name: ${s.name}`, `Manual total: ${Number(totals.manual.toFixed(3))} min`, `Auto total: ${Number(totals.auto.toFixed(3))} min`,
        `Starts with a part: ${s.has_part ? 'Yes' : 'No'}`, `Position: (${s.x}, ${s.y})`, `Size: ${s.w} × ${s.h}`];
    stationProcesses(s).forEach((process, index) => lines.push(`Process ${index + 1}: ${process.name} — manual ${process.manual_time}, auto ${process.auto_time} min`));
    const known = new Set(['name', 'processes', 'cycle_time', 'has_part', 'x', 'y', 'w', 'h', 'next_process_id']);
    Object.entries(s).filter(([key]) => !known.has(key)).forEach(([key, value]) => lines.push(`${key}: ${typeof value === 'object' ? JSON.stringify(value) : value}`));
    lines.push(`Has part now: ${machine.hasPart ? 'Yes' : 'No'}`);
    lines.push(`Machine: ${machine.busy ? machine.phase : 'Idle'}`);
    if (machine.busy) {
        lines.push(`Current process: ${machine.processName}`);
        lines.push(`Time to completion: ${Math.max(0, machine.until - opState.time).toFixed(2)} min`);
        if (machine.phase === 'manual') lines.push(`Working operator: ${machine.operator}`);
    }
    const blocked = opNames.filter(op => String(opState.blockedLoc[op]) === sid && opState.isBlocked[op]);
    blocked.forEach(op => lines.push(`Blocked: ${opState.blockedReason[op] || op}`));
    tooltip.textContent = lines.join('\n');
    tooltip.hidden = false;
    const rect = tooltip.getBoundingClientRect();
    tooltip.style.left = Math.max(8, Math.min(hoverPointer.clientX + 14, window.innerWidth - rect.width - 8)) + 'px';
    tooltip.style.top = Math.max(8, Math.min(hoverPointer.clientY + 14, window.innerHeight - rect.height - 8)) + 'px';
}

let scenario     = null;
let positions    = null;
let partImage    = null;
let lineDirectionImage = null;
let simEvents    = [];
let taktTime     = 30;
let opNames      = [];

let opState        = null;
let isRunning       = false;
let simClock        = 0.0;
let simulationTime  = 0.0;
let taktResetCount  = 0;
let lastFrameTime   = null;
const baseMsPerSimMinute  = 1000; // "1.0x" reference speed: 1 sim-min = 1 real-sec
let   speedMultiplier     = 1.0;
let   msPerSimMinute      = baseMsPerSimMinute / speedMultiplier;

const timeline = document.getElementById('timeline');
const timelineLabel = document.getElementById('timeline-label');
const playButton = document.getElementById('start-btn');
const pauseButton = document.getElementById('stop-btn');
const restartButton = document.getElementById('restart-btn');
const exportSwsButton = document.getElementById('export-sws-btn');
const exportSwcsButton = document.getElementById('export-swcs-btn');
exportSwsButton.addEventListener('click', () => {window.location.assign('/export-sws');});
exportSwcsButton.addEventListener('click', () => {window.location.assign('/export-swcs');});
let totalDuration = 0;

function updatePlaybackControls() {
    timeline.value = simulationTime;
    timelineLabel.textContent = `${simulationTime.toFixed(2)} / ${totalDuration.toFixed(2)} min`;
    timeline.setAttribute('aria-valuetext', `${simulationTime.toFixed(2)} of ${totalDuration.toFixed(2)} minutes`);
    playButton.disabled = !opState || !!opState.stopReason || opState.finished;
    pauseButton.disabled = !isRunning;
    restartButton.disabled = !opState;
    statusText.style.color = '';
    statusText.style.fontWeight = '';
    if (opState?.stopReason) {
        statusText.textContent = '⛔ SIMULATION STOPPED — ' + opState.stopReason;
        statusText.style.color = '#cc0000';
        statusText.style.fontWeight = 'bold';
    } else if (opState?.finished) {
        statusText.textContent = 'Simulation complete — 100 takt periods.';
    } else if (opState) {
        statusText.textContent = isRunning ? 'Playing simulation.' : 'Paused. Press PLAY to continue.';
    }
}

function pausePlayback() {
    isRunning = false;
    lastFrameTime = null;
    updatePlaybackControls();
}

function seekTo(targetTime) {
    if (!scenario || !opState || !Number.isFinite(targetTime)) return;
    isRunning = false;
    lastFrameTime = null;
    // Events mutate state in forward order. Rebuild first so backward seeks
    // restore inventory, parts, machine phases and error/completion flags.
    initOperatorState();
    updateOperators(opState, Math.max(0, Math.min(targetTime, totalDuration)));
    simulationTime = opState.time;
    taktResetCount = Math.floor(simulationTime / taktTime);
    simClock = simulationTime % taktTime;
    updatePlaybackControls();
    drawFrame(performance.now());
}

timeline.addEventListener('pointerdown', pausePlayback);
timeline.addEventListener('input', () => seekTo(Number(timeline.value)));
restartButton.addEventListener('click', () => seekTo(0));

// ============================================================
// PART — Speed dial control
// ============================================================
const speedDial  = document.getElementById("speed-dial");
const speedLabel = document.getElementById("speed-label");

speedDial.addEventListener("input", () => {
    speedMultiplier  = parseFloat(speedDial.value);
    msPerSimMinute   = baseMsPerSimMinute / speedMultiplier;
    speedLabel.textContent = speedMultiplier.toFixed(2) + "x";
});

// ============================================================
// PART 2 — Image loading helper
// ============================================================
function loadImage(src) {
    return new Promise((resolve) => {
        const img = new Image();
        img.onload  = () => resolve(img);
        img.onerror = () => resolve(img);
        img.src = src;
    });
}

// ============================================================
// PART 3 — Buttons
// ============================================================
document.getElementById("start-btn").addEventListener("click", () => {
    if (!opState || opState.stopReason || opState.finished) return;
    isRunning = true;
    lastFrameTime = null;
    updatePlaybackControls();
});

document.getElementById("stop-btn").addEventListener("click", pausePlayback);

document.getElementById("back-btn").addEventListener("click", () => {
    window.location.href = "/builder";
});

// ============================================================
// PART 4 — Load scenario + events, then initialize
// ============================================================
function initOperatorState() {
    // Use one natural numeric order in operator chips, canvas legend,
    // playback drawing, and legend hover hit targets.
    opNames = sortOperatorIds(Object.keys(scenario.operators));
    positions = buildPositionsFromScenario(scenario);

    opState = buildOperatorState(
        simEvents,
        positions.stationCenters,
        positions.boxCenters,
        opNames,
        scenario
    );
}

async function init() {
    try {
        partImage = await loadImage(canvas.dataset.partImageUrl);
        lineDirectionImage = await loadImage(canvas.dataset.lineDirectionImageUrl);

        const data = await requestJson('/events');
        if (data.event_schema_version !== Number(document.body.dataset.eventSchemaVersion)) {
            throw new Error('Unsupported simulation event format. Refresh the page and run the simulation again.');
        }


        if (!data.scenario || !data.events || data.events.length === 0) {
            statusText.textContent = "No simulation has been run yet. Go back to the builder and click Run Simulation.";
            return;
        }

        scenario  = data.scenario;
        simEvents = data.events;
        taktTime  = data.takt_time;
        document.getElementById('physical-walking-summary').textContent =
            `Physical scale: ${Number(scenario.layout_scale_px_per_m ?? 50).toFixed(0)} px/m · ` +
            `Operator walking speed: ${Number(scenario.walking_speed_m_per_s ?? 1.2).toFixed(2)} m/s ` +
            '(separate from playback speed)';

        initOperatorState();
        exportSwsButton.disabled = false;
        exportSwcsButton.disabled = false;
        renderStartingSwipChart();
        populateHighlightLegend();
        totalDuration = simEvents.reduce((latest, event) => Math.max(latest, event.time), 0);
        timeline.max = totalDuration;
        timeline.disabled = totalDuration <= 0;
        updatePlaybackControls();
        statusText.textContent = "Ready. Press PLAY.";
        requestAnimationFrame(animationLoop);
    } catch (err) {
        console.error("Error during init():", err);
        statusText.textContent = "Error loading simulation: " + err.message;
    }
}

init();

// ============================================================
// PART 5 — Main animation loop
// ============================================================
function animationLoop(timestamp) {
    if (lastFrameTime === null) lastFrameTime = timestamp;
    const deltaMs = timestamp - lastFrameTime;
    lastFrameTime = timestamp;

    if (isRunning && opState) {
        simulationTime += deltaMs / msPerSimMinute;
        updateOperators(opState, simulationTime);
        simulationTime = opState.time;
        taktResetCount = Math.floor(simulationTime / taktTime);
        simClock = simulationTime % taktTime;

        if (opState.finished || opState.stopReason) {
            isRunning = false;
        }
        updatePlaybackControls();
    }

    drawFrame(timestamp);
    requestAnimationFrame(animationLoop);
}
// ============================================================
// PART 6 — Drawing
// ============================================================
function drawFrame(timestamp) {
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!scenario || !opState) return;

    ctx.save();
    view.apply(ctx);

    const activeOperator = activeHighlightOperator();
    // Recompute visited locations only when the operator focus changes.
    // No scenario/event changes: this is purely visual.
    const dimAlpha = 0.18;

    // ---- draw boxes ----
    for (const bid in positions.boxPositions) {
        ctx.save();
        if (activeOperator && !highlightedLocations.has(bid)) ctx.globalAlpha = dimAlpha;
        drawBox(ctx, bid, positions.boxPositions[bid], scenario.boxes[bid],
                opState.boxState[bid], partImage, timestamp, lineDirectionImage);
        ctx.restore();
    }

    // ---- draw stations ----
    for (const sid in positions.stationPositions) {
        const machine = opState.stationState[sid];
        const activeColor = machine.phase === 'automatic' ? '#c9def6' : scenario.operators[machine.operator]?.color || '#c8c8c8';
        ctx.save();
        if (activeOperator && !highlightedLocations.has(sid)) ctx.globalAlpha = dimAlpha;
        drawStation(ctx, sid, positions.stationPositions[sid], scenario.stations[sid], machine.busy, activeColor);
        if (machine.busy) {
            const pos = positions.stationPositions[sid];
            ctx.fillStyle = '#173963';
            ctx.font = '11px Arial';
            ctx.textBaseline = 'alphabetic';
            const processText = `Process: ${machine.processName || machine.process || '—'}`;
            ctx.fillText(processText, pos.x, pos.y - 18);
            ctx.fillText(`${machine.phase === 'automatic' ? 'AUTO' : 'MANUAL'} · ${Math.max(0, machine.until - opState.time).toFixed(1)}m`, pos.x, pos.y - 6);
        }
        ctx.restore();
    }

    // ---- draw dropped parts sitting at stations/boxes ----
    // (drawn AFTER stations so the icon is visible on top of the
    // station's solid rectangle, instead of hidden underneath it)
    for (const key in opState.droppedParts) {
        const p = opState.droppedParts[key];
        ctx.save();
        if (activeOperator && !highlightedLocations.has(key)) ctx.globalAlpha = dimAlpha;
        drawPart(ctx, p.x, p.y, partImage);
        ctx.restore();
    }

    // ---- draw operator motion tracers ----
    opNames.forEach(op => {
        const baseColor = scenario.operators[op].color;
        const color = opState.isBlocked[op] ? [120, 120, 120] : baseColor;
        ctx.save();
        if (activeOperator && activeOperator !== op) ctx.globalAlpha = dimAlpha;
        drawOperatorTracer(ctx, opState.traces[op], color, opState.time);
        ctx.restore();
    });

    // ---- draw operators and the parts they carry ----
    opNames.forEach(op => {
        ctx.save();
        if (activeOperator && activeOperator !== op) ctx.globalAlpha = dimAlpha;
        const pos       = opState.opPositions[op];
        const baseColor = scenario.operators[op].color;
        const color     = opState.isBlocked[op] ? [120, 120, 120] : baseColor;

        const partPos = opState.partPositions[op];
        if (partPos) {
            drawPart(ctx, partPos.x, partPos.y, partImage);
        }

        drawOperator(ctx, op, pos.x, pos.y, color);
        if (opState.moves[op]) {
            const move = opState.moves[op];
            ctx.save();
            ctx.fillStyle = '#1e3c78';
            ctx.font = '10px Arial'; ctx.textAlign = 'center';
            ctx.fillText(`${Number(move.distance_m || 0).toFixed(2)} m · ${Number(move.walking_speed_m_per_s || scenario.walking_speed_m_per_s || 1.2).toFixed(2)} m/s`, pos.x, pos.y + 28);
            ctx.restore();
        }

        if (opState.isBlocked[op]) {
            ctx.fillStyle    = "#cc0000";
            ctx.font         = "10px Arial";
            ctx.textAlign    = "center";
            ctx.fillText("BLOCKED", pos.x, pos.y + 26);
            ctx.textAlign    = "left";
        }
        ctx.restore();
    });

    ctx.restore();
    drawBanner(ctx, simClock, taktTime, taktResetCount, canvas.width);
    updateStationTooltip();
    // ---- legend ----
    drawLegend(ctx, opNames, scenario.operators, partImage, canvas.height, activeOperator);

    // ---- paused overlay ----
    if (!isRunning) {
        ctx.fillStyle = "rgba(30, 60, 120, 0.10)";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = "rgba(30, 60, 120, 0.9)";
        ctx.fillRect(canvas.width / 2 - 280, canvas.height - 100, 560, 50);
        ctx.fillStyle    = "#ffffff";
        ctx.font         = "28px Arial";
        ctx.textAlign    = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(opState.stopReason ? "STOPPED — See status above" : opState.finished ? "SIMULATION COMPLETE" : "PAUSED — Press PLAY to continue", canvas.width / 2, canvas.height - 75);
        ctx.textAlign    = "left";
        ctx.textBaseline = "alphabetic";
    }
}
