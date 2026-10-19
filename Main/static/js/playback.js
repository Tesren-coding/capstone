import {CanvasViewport, stationProcesses, stationTotals} from "./canvas-tools.js";
import {drawBox, drawStation, drawPart, drawOperator, drawOperatorTracer, drawBanner, drawLegend} from "./draw.js";
import {buildPositionsFromScenario} from "./positions.js";
import {buildOperatorState, updateOperators} from "./state.js";
import {requestJson} from "./api.js";
import {visitedLocationsForOperator, operatorAtLegendPoint} from "./operator-highlight.js";

// playback.js — Simulation playback, controls and tooltips.
// ============================================================
// PART 1 — Setup variables
// ============================================================
const canvas     = document.getElementById("sim-canvas");
const ctx        = canvas.getContext("2d");
const statusText = document.getElementById("status-text");

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
        button.setAttribute('aria-label', `Highlight ${operator.name || id}'s work area`);
        button.setAttribute('aria-pressed', 'false');
        button.style.cssText = 'display:inline-flex;align-items:center;gap:6px;padding:7px 11px;background:#fff;border:1px solid #9cacc1;border-radius:18px;cursor:pointer;font-size:13px;';
        const swatch = document.createElement('span');
        swatch.style.cssText = `display:inline-block;width:12px;height:12px;border-radius:50%;background:${Array.isArray(operator.color) ? `rgb(${operator.color.join(',')})` : operator.color || '#888'};`;
        button.append(swatch, document.createTextNode(operator.name || id));
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
        if (machine.phase === 'manual') lines.push(`Working operator: ${scenario.operators[machine.operator]?.name || machine.operator}`);
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
    opNames = Object.keys(scenario.operators);
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

        drawOperator(ctx, scenario.operators[op].name || op, pos.x, pos.y, color);
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
