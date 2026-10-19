import {CanvasViewport, drawStationText, stationProcesses, stationTotals, escapeHtml} from "./canvas-tools.js";
import {installDrag,dragHandle,moveBefore,rowDrop,beforeFromDrop} from "./drag-sort.js";
import {requestJson, postJson} from "./api.js";
import {orderedOperatorIds, remapOperatorOrder} from "./operator-order.js";
import {STATION_WIDTH, STATION_HEIGHT} from "./layout-geometry.js";
import {drawDirection, directionContainsPoint, directionResizeHandle,
    resizeDirectionFromPoint, DIRECTION_MIN_WIDTH, DIRECTION_MIN_HEIGHT} from "./line-direction.js";
import {OPERATOR_RADIUS, SIDES, operatorPoint, operatorSlots, nearestOperatorSlot,
    stationInsertPosition, snapStation, updateAttachedOperators, detachStationOperators,
    remapOperatorAttachments} from "./builder-snapping.js";
import {smartSnapRect, nearestGapMeasurements, drawSmartGuides, meterLabel} from "./smart-guides.js";
import {stationCorner,hitStationCorner,resizeStationRect,nearestDimensionPoint,
    resolvedDimension,dimensionLinePoints,dimensionOffsetFromDrag,distanceFromSegment,drawDimension,drawStationDimensions,
    drawStationHandles,MIN_STATION_WIDTH,MIN_STATION_HEIGHT} from "./dimension-tools.js";

// builder.js — Scenario builder behavior.
// ============================================================
// PART 1 — Canvas + state setup
// ============================================================
const canvas     = document.getElementById("builder-canvas");
const ctx        = canvas.getContext("2d");
const statusText = document.getElementById("status-text");
const scaleInput = document.getElementById('layout-scale-input');
const walkSpeedInput = document.getElementById('walk-speed-input');
const smartSnapInput = document.getElementById('smart-guide-toggle');
const DEFAULT_PX_PER_M = 50;
const DEFAULT_WALK_M_PER_S = 1.2;

const lineDirectionImage = new Image();
lineDirectionImage.onload = () => drawFrame();
if (canvas.dataset.lineDirectionImageUrl) lineDirectionImage.src = canvas.dataset.lineDirectionImageUrl;

const scenario = {
    stations:  {},
    operators: {},
    boxes:     {},
    dimensions: {}, // Saved independent measurements, optionally anchored to layout items.
};

const view = new CanvasViewport(canvas, document.getElementById('canvas-controls'), () => drawFrame());
const schemaVersion = Number(document.body.dataset.scenarioSchemaVersion);
let scenarioExtras = {};
let suggestedFilename = 'scenario.json';
let loadedFilename = null;
let loadedRevision = null;
let lastSavedSnapshot = null;
let freshLineSnapshot = null; // unchanged defaults do not require a discard warning
const DRAFT_KEY = 'capstone-builder-draft';
const HANDOFF_KEY = 'capstone-builder-handoff';
let reviewSnapshot=null,reviewRequest=0;

let nextStationId  = 1;
let nextBoxId       = 1;
let nextDimensionId = 1;

const SIZES = {
    station: { w: STATION_WIDTH, h: STATION_HEIGHT },
    swip:    { w: 90,  h: 60 },
    in:      { w: 90,  h: 60 },
    out:     { w: 90,  h: 60 },
    direction: { w: 875, h: 85 },
};

const DEFAULT_COLORS = [
    [220, 60, 60], [60, 120, 220], [60, 180, 90],
    [230, 160, 30], [150, 60, 200], [30, 170, 170],
];
let colorIndex = 0;

let draggedItem  = null;
let dragOffset   = { x: 0, y: 0 };
let selectedItem = null;
let placingType  = null;
let placementPreview = null;
let dragStart = null;
// Canvas-only selection state: never included in saved scenario data.
const selectedKeys = new Set();
let marquee = null;   // {start, current, base} in world coordinates
let groupDrag = null; // {start, original} snapshot for translating a selection
// The operator sequence step currently being edited; this is UI-only state.
let standingPointEditor = null; // {operatorId, stepIndex}
let pendingStandingClick = null; // defer click until mouseup so operators remain draggable
let smartGuideData = null; // Only visible while dragging or previewing; never saved.
let draggingWithoutSnap = false;
let dimensionTool = false;
let dimensionStart = null; // {x,y,anchor} once first endpoint is picked
let dimensionPreview = null;

function snapTargets(excluded = new Set()) {
    // The direction graphic is measured using its rotated bounding rectangle.
    // Exclude operators: their home attachment points must not redirect stations.
    return allItems().filter(item => !['operator','dimension'].includes(item.type) &&
        !excluded.has(selectionKey(item.type, item.id)))
        .map(item => ({type:item.type==='station'?'station':'box', id:item.id, rect:itemBounds(item)}));
}
function guidePosition(rect, excludes, dockStations=false) {
    // Alt temporarily disables snapping but still displays the physical gap.
    const result = smartSnapRect(rect, snapTargets(excludes), view.scale,
        {dockStations, snap:!!smartSnapInput?.checked && !draggingWithoutSnap});
    smartGuideData = smartSnapInput?.checked ? result : null;
    return result;
}

function validStandingStep(operatorId, index) {
    const op = scenario.operators[operatorId];
    return Number.isInteger(index) && !!op?.sequence?.[index] &&
        !!scenario.stations[op.sequence[index].loc];
}
function syncStandingPointEditor(operatorId) {
    if (!operatorId) { standingPointEditor = null; return; }
    if (standingPointEditor?.operatorId === operatorId &&
        validStandingStep(operatorId, standingPointEditor.stepIndex)) return;
    const next = scenario.operators[operatorId]?.sequence?.findIndex(step =>
        !!scenario.stations[step.loc]) ?? -1;
    standingPointEditor = next >= 0 ? {operatorId, stepIndex:next} : null;
}
function activeStandingSlots() {
    if (placingType || selectedItem?.type !== 'operator' || selectedKeys.size !== 1 ||
        !standingPointEditor || standingPointEditor.operatorId !== selectedItem.id ||
        !validStandingStep(standingPointEditor.operatorId, standingPointEditor.stepIndex)) return [];
    const step = scenario.operators[standingPointEditor.operatorId].sequence[standingPointEditor.stepIndex];
    return SIDES.map(side => ({side, stationId:step.loc,
        ...operatorPoint(scenario.stations[step.loc], side), selected:step.standing_side === side}));
}
function standingSlotAt(point) {
    const limit = Math.max(OPERATOR_RADIUS, 13 / view.scale);
    return activeStandingSlots().find(slot => Math.hypot(point.x-slot.x, point.y-slot.y) <= limit) || null;
}
const selectionKey = (type, id) => `${type}:${id}`;

function itemForKey(key) {
    const split = key.indexOf(':');
    const type = key.slice(0, split), id = key.slice(split + 1);
    const collection = type === 'station' ? scenario.stations :
        type === 'operator' ? scenario.operators :
        type === 'dimension' ? scenario.dimensions : scenario.boxes;
    return collection[id] ? {type, id, pos: collection[id]} : null;
}
function setSelectedKeys(keys) {
    selectedKeys.clear();
    for (const key of keys) if (itemForKey(key)) selectedKeys.add(key);
    selectedItem = selectedKeys.size === 1 ? itemForKey([...selectedKeys][0]) : null;
    syncStandingPointEditor(selectedItem?.type === 'operator' ? selectedItem.id : null);
    if (selectedKeys.size > 1) {
        panelTitle.textContent = `${selectedKeys.size} items selected`;
        panelFields.innerHTML = '<p>Drag any selected item to move the group. Ctrl-click to add or remove items. All station/operator connections are maintained when their station moves.</p>';
        deleteItemBtn.textContent = `Delete ${selectedKeys.size} Selected`;
        sidePanel.style.display = 'block';
    } else {
        deleteItemBtn.textContent = 'Delete';
        openSidePanel(selectedItem);
    }
}
function allItems() {
    return [
        ...Object.entries(scenario.stations).map(([id,pos]) => ({type:'station',id,pos})),
        ...Object.entries(scenario.operators).map(([id,pos]) => ({type:'operator',id,pos})),
        ...Object.entries(scenario.boxes).map(([id,pos]) => ({type:'box',id,pos})),
        ...Object.entries(scenario.dimensions).map(([id,pos]) => ({type:'dimension',id,pos})),
    ];
}
function rectFromPoints(a, b) {
    return {x: Math.min(a.x,b.x), y: Math.min(a.y,b.y),
        w: Math.abs(b.x-a.x), h: Math.abs(b.y-a.y)};
}
function dimensionBounds(type,id) {
    if(type==='station') return scenario.stations[id] || null;
    const box=scenario.boxes[id];
    return box ? itemBounds({type:'box',id,pos:box}) : null;
}
function dimensionPoints(d) { return resolvedDimension(d,dimensionBounds); }
function dimensionSnapPoint(mouse) {
    return nearestDimensionPoint(mouse,snapTargets(),view.scale);
}
function dimensionAt(mouse) {
    if(selectedItem?.type==='dimension') {
        const dim=scenario.dimensions[selectedItem.id];
        if(dim) {
            const points=dimensionPoints(dim);
            for(const which of ['start','end']) {
                if(Math.hypot(mouse.x-points[which].x,mouse.y-points[which].y)<=10/view.scale)
                    return {type:'dimension-endpoint',id:selectedItem.id,pos:dim,which};
            }
        }
    }
    for(const [id,dim] of Object.entries(scenario.dimensions)) {
        const points=dimensionLinePoints(dim,dimensionBounds);
        // Accept the ruler's label as a drag target too, not just its thin line.
        const labelX=(points.start.x+points.end.x)/2+points.nx*17/view.scale;
        const labelY=(points.start.y+points.end.y)/2+points.ny*17/view.scale;
        if(distanceFromSegment(mouse,points.start,points.end)<=7/view.scale ||
            (Math.abs(mouse.x-labelX)<=29/view.scale && Math.abs(mouse.y-labelY)<=11/view.scale))
            return {type:'dimension',id,pos:dim};
    }
    return null;
}
function updateDimensionPanel() {
    if(selectedItem?.type!=='dimension') return;
    const dim=scenario.dimensions[selectedItem.id];
    const output=document.getElementById('field-dimension-length');
    if(dim&&output) {
        const {start,end}=dimensionPoints(dim);
        output.textContent=meterLabel(Math.hypot(end.x-start.x,end.y-start.y),Number(scaleInput.value));
    }
}
function remapDimensionAnchors(mapping) {
    for(const dim of Object.values(scenario.dimensions)) {
        for(const key of ['start_anchor','end_anchor']) {
            const a=dim[key];
            if(a?.type==='station' && Object.hasOwn(mapping,a.id)) a.id=String(mapping[a.id]);
        }
    }
}
function releaseDeletedDimensionAnchors(type,id) {
    for(const dim of Object.values(scenario.dimensions)) {
        const points=dimensionPoints(dim);
        for(const [which,coord] of [['start',points.start],['end',points.end]]) {
            const anchor=dim[`${which}_anchor`];
            if(anchor?.type===type && anchor.id===String(id)) {
                if(which==='start'){dim.x=coord.x;dim.y=coord.y;}
                else{dim.x2=coord.x;dim.y2=coord.y;}
                dim[`${which}_anchor`]=null;
            }
        }
    }
}
function rectIntersects(a, b) {
    return a.x <= b.x + b.w && a.x + a.w >= b.x &&
        a.y <= b.y + b.h && a.y + a.h >= b.y;
}
function itemBounds(item) {
    const b = item.pos;
    if (item.type === 'operator') return {x:b.x-OPERATOR_RADIUS,y:b.y-OPERATOR_RADIUS,w:OPERATOR_RADIUS*2,h:OPERATOR_RADIUS*2};
    if (item.type === 'dimension') {
        const {start,end}=dimensionLinePoints(b,dimensionBounds);
        const padding=5/Math.max(.05,view.scale);
        return {x:Math.min(start.x,end.x)-padding,y:Math.min(start.y,end.y)-padding,
                w:Math.abs(end.x-start.x)+padding*2,h:Math.abs(end.y-start.y)+padding*2};
    }
    if (item.type !== 'box' || b.type !== 'direction') return b;
    const a = (b.rotation || 0) * Math.PI / 180;
    const w = Math.abs(b.w*Math.cos(a))+Math.abs(b.h*Math.sin(a));
    const h = Math.abs(b.w*Math.sin(a))+Math.abs(b.h*Math.cos(a));
    return {x:b.x+b.w/2-w/2, y:b.y+b.h/2-h/2, w, h};
}
function hitSelection(rect) {
    return allItems().filter(item => rectIntersects(rect,itemBounds(item)))
        .map(item => selectionKey(item.type,item.id));
}
function beginGroupDrag(start) {
    const objects=[...selectedKeys].map(itemForKey).filter(Boolean);
    const bounds=objects.map(itemBounds);
    const x=Math.min(...bounds.map(b=>b.x)), y=Math.min(...bounds.map(b=>b.y));
    const w=Math.max(...bounds.map(b=>b.x+b.w))-x;
    const h=Math.max(...bounds.map(b=>b.y+b.h))-y;
    groupDrag = {start, bounds:{x,y,w,h}, original: new Map([...selectedKeys].map(key => {
        const item = itemForKey(key);
        return [key, {x:item.pos.x, y:item.pos.y, attached_to:item.pos.attached_to,
            points:item.type==='dimension'?dimensionPoints(item.pos):null}];
    }))};
}
function moveGroup(to) {
    let dx=to.x-groupDrag.start.x, dy=to.y-groupDrag.start.y;
    const b=groupDrag.bounds;
    const result=guidePosition({x:b.x+dx,y:b.y+dy,w:b.w,h:b.h},selectedKeys);
    dx=result.x-b.x; dy=result.y-b.y;
    const movingStations = new Set([...selectedKeys].filter(k=>k.startsWith('station:')).map(k=>k.slice(8)));
    const movingBoxes = new Set([...selectedKeys].filter(k=>k.startsWith('box:')).map(k=>k.slice(4)));
    // Move all selected stations first without single-station snap, preserving the group arrangement.
    for (const key of selectedKeys) {
        const item=itemForKey(key), original=groupDrag.original.get(key);
        if (!item || !original || ['operator','dimension'].includes(item.type)) continue;
        item.pos.x=original.x+dx; item.pos.y=original.y+dy;
    }
    for (const key of selectedKeys) {
        const item=itemForKey(key), original=groupDrag.original.get(key);
        if (!item || !original || item.type!=='operator') continue;
        // Operator attached to a station in the group follows its station once, not twice.
        if (item.pos.attached_to && movingStations.has(item.pos.attached_to.station_id)) continue;
        if (item.pos.attached_to && (dx!==0 || dy!==0)) delete item.pos.attached_to;
        item.pos.x=original.x+dx; item.pos.y=original.y+dy;
    }
    for (const id of movingStations) updateAttachedOperators(scenario.stations, scenario.operators, id);
    // Dimension anchors follow selected stations/boxes. Endpoints referring
    // to outside objects become free points when their ruler is grouped/moved.
    for (const key of selectedKeys) {
        const item=itemForKey(key), original=groupDrag.original.get(key);
        if(item?.type!=='dimension'||!original) continue;
        for(const [which,point] of [['start',original.points.start],['end',original.points.end]]) {
            const anchor=item.pos[`${which}_anchor`];
            const follows=anchor && (anchor.type==='station'?movingStations.has(anchor.id):movingBoxes.has(anchor.id));
            if(follows) continue;
            if(which==='start') {item.pos.x=point.x+dx;item.pos.y=point.y+dy;}
            else {item.pos.x2=point.x+dx;item.pos.y2=point.y+dy;}
            item.pos[`${which}_anchor`]=null;
        }
    }
}

function snapOperatorToSlot(op, x, y, ignoreId = null) {
    const slot = nearestOperatorSlot(scenario.stations, scenario.operators, x, y, view.scale, ignoreId);
    if (slot) {
        op.x = slot.x; op.y = slot.y;
        op.attached_to = {station_id: slot.station_id, side: slot.side};
    } else {
        op.x = x; op.y = y;
        delete op.attached_to;
    }
    return slot;
}

function moveStation(id, x, y) {
    const station = scenario.stations[id];
    const result=guidePosition({x,y,w:station.w,h:station.h},
        new Set([selectionKey('station',id)]), true);
    station.x=result.x;station.y=result.y;
    updateAttachedOperators(scenario.stations, scenario.operators, id);
    return result;
}

// ============================================================
// PART 2 — Placement mode
// ============================================================
const cancelPlaceBtn = document.getElementById("cancel-place-btn");

document.querySelectorAll(".add-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        stopDimensionTool();
        placingType = btn.getAttribute("data-type");
        canvas.style.cursor = "crosshair";
        cancelPlaceBtn.style.display = "inline-block";
        placementPreview = null;
        statusText.textContent = placingType === 'operator'
            ? 'Place near a dotted circle to attach the operator to a station side.'
            : placingType === 'station' ? 'New stations align and snap next to existing stations.'
            : `Click on the canvas to place a new ${placingType}.`;
        drawFrame();
    });
});

cancelPlaceBtn.addEventListener("click", () => {
    exitPlacementMode();
    statusText.textContent = "Placement cancelled.";
});

const dimensionToolBtn=document.getElementById('dimension-tool-btn');
function stopDimensionTool() {
    dimensionTool=false;dimensionStart=null;dimensionPreview=null;
    dimensionToolBtn.setAttribute('aria-pressed','false');
    dimensionToolBtn.classList.remove('active-tool');
    if(!placingType) canvas.style.cursor='default';
}
dimensionToolBtn.addEventListener('click', () => {
    if(dimensionTool) {
        stopDimensionTool();
        statusText.textContent='Dimension tool disabled.';
    } else {
        exitPlacementMode();
        setSelectedKeys([]);
        dimensionTool=true;dimensionStart=null;dimensionPreview=null;
        dimensionToolBtn.setAttribute('aria-pressed','true');
        dimensionToolBtn.classList.add('active-tool');
        canvas.style.cursor='crosshair';
        statusText.textContent='Dimension: click two points on object edges. Drag the resulting dimension line away from the edges; dotted witness lines keep the measurement attached. Escape cancels.';
    }
    drawFrame();
});
function exitPlacementMode() {
    placingType = null;
    placementPreview = null;
    smartGuideData = null;
    canvas.style.cursor = "default";
    cancelPlaceBtn.style.display = "none";
}

// ============================================================
// PART 3 — Create new items
// ============================================================
function createStation(x, y) {
    const id = nextStationId++;
    const position = stationInsertPosition(scenario.stations, x, y,
        SIZES.station.w, SIZES.station.h, view.scale);
    scenario.stations[id] = {
        x: position.x,
        y: position.y,
        w: SIZES.station.w,
        h: SIZES.station.h,
        name: "New Station",
        cycle_time: 10,
        processes: [{id: 'p1', name: 'Process 1', manual_time: 10, auto_time: 0}],
        has_part: false,
    };
    return id;
}

// Operator identity is the display name. Reuse the lowest free number so
// deleting Op2 then creating an operator yields Op2 again, not Op4.
function nextAvailableOperatorId() {
    let number = 1;
    while (Object.hasOwn(scenario.operators, `Op${number}`)) number++;
    return `Op${number}`;
}

const operatorOrderPanel = document.getElementById('operator-order-panel');
const operatorOrderList = document.getElementById('operator-order-list');
const reorderOperatorsButton = document.getElementById('reorder-operators-btn');
let operatorOrderSignature = null;

function renderOperatorOrderList(force = false) {
    if (operatorOrderPanel.hidden) return;
    const ids = orderedOperatorIds(scenario.operators);
    // Don't rebuild rows while a drag is starting or in progress.
    const signature = ids.map(id => `${id}:${scenario.operators[id].color?.join(',') || ''}:${(scenario.operators[id].sequence || []).map(step => step.loc).join(',')}`).join('|');
    if (!force && signature === operatorOrderSignature) return;
    operatorOrderSignature = signature;
    if (!ids.length) {
        operatorOrderList.innerHTML = '<li>No operators yet. Use + Operator to create one.</li>';
        return;
    }
    operatorOrderList.innerHTML = ids.map(id => {
        const op = scenario.operators[id];
        const color = Array.isArray(op.color) ? rgbToHex(op.color) : '#64748b';
        const count = op.sequence?.length || 0;
        const places = (op.sequence || []).map(step => {
            const loc = String(step.loc ?? '');
            if (scenario.stations[loc]) return `S${loc}`;
            if (scenario.boxes[loc]) return scenario.boxes[loc].name || scenario.boxes[loc].type.toUpperCase();
            return '';
        }).filter(Boolean);
        const preview = places.length ? places.slice(0,3).join(' → ') + (places.length > 3 ? ' …' : '') : 'No assigned locations';
        return `<li data-operator-order-id="${escapeHtml(id)}">
            ${dragHandle('operator-order', id, id)}
            <span class="operator-color-swatch" style="background:${color};"></span>
            <strong>${escapeHtml(id)}</strong>
            <span style="font-size:12px;color:#526173;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${escapeHtml(preview)}">${escapeHtml(preview)}</span>
            <span style="font-size:12px;color:#526173;white-space:nowrap;">${count} step${count === 1 ? '' : 's'}</span>
        </li>`;
    }).join('');
}

function setOperatorOrderPanel(open) {
    operatorOrderPanel.hidden = !open;
    reorderOperatorsButton.setAttribute('aria-expanded', String(open));
    if (open) renderOperatorOrderList(true);
}
reorderOperatorsButton.addEventListener('click', () => setOperatorOrderPanel(operatorOrderPanel.hidden));
document.getElementById('operator-order-close').addEventListener('click', () => setOperatorOrderPanel(false));

// Renumber operator identities against the requested top-to-bottom order.
// No station/box IDs change: an operator's sequence belongs to their object.
function applyOperatorOrder(ids) {
    const {operators, mapping, changed} = remapOperatorOrder(scenario.operators, ids);
    if (!changed) return false;
    recordUndo();
    redoStack.length = 0;
    const previousSelection = [...selectedKeys];
    const previousStanding = standingPointEditor;
    for (const id of Object.keys(scenario.operators)) delete scenario.operators[id];
    Object.assign(scenario.operators, operators);
    draggedItem = null;
    setSelectedKeys(previousSelection.map(key => {
        const [type, id] = key.split(':');
        return type === 'operator' && mapping[id] ? selectionKey(type, mapping[id]) : key;
    }));
    if (previousStanding && mapping[previousStanding.operatorId] &&
        selectedItem?.type === 'operator' && selectedItem.id === mapping[previousStanding.operatorId] &&
        validStandingStep(selectedItem.id, previousStanding.stepIndex)) {
        standingPointEditor = {...previousStanding, operatorId: selectedItem.id};
    }
    renderOperatorOrderList(true);
    drawFrame();
    rememberDraft();
    statusText.textContent = `Operator order updated: ${ids.map(id => `${id} → ${mapping[id]}`).join(', ')}. Assignments and colors preserved.`;
    return true;
}

installDrag(operatorOrderList, {
    source(node) {
        if (node.dataset.dragType !== 'operator-order' || !scenario.operators[node.dataset.dragId]) return null;
        return {type: 'operator-order', id: node.dataset.dragId, label: node.dataset.dragId};
    },
    target(hit, event) {
        const row = hit.closest('[data-operator-order-id]');
        return row && operatorOrderList.contains(row)
            ? {...rowDrop(row, event.clientY), id: row.dataset.operatorOrderId} : null;
    },
    drop(data, where) {
        const ids = orderedOperatorIds(scenario.operators);
        const before = beforeFromDrop(ids, where.id, where.after, id => id);
        if (moveBefore(ids, data.id, before, id => id)) applyOperatorOrder(ids);
    },
    keyboard(data, key) {
        const ids = orderedOperatorIds(scenario.operators);
        const index = ids.indexOf(data.id);
        const target = index + (['ArrowUp', 'ArrowLeft'].includes(key) ? -1 : 1);
        if (target < 0 || target >= ids.length) return;
        const moving = ids.splice(index, 1)[0];
        ids.splice(target, 0, moving);
        const mapping = Object.fromEntries(ids.map((id, i) => [id, `Op${i + 1}`]));
        if (applyOperatorOrder(ids)) {
            operatorOrderList.querySelector(`[data-drag-id="${mapping[data.id]}"]`)?.focus();
        }
    },
});

function createOperator(x, y) {
    const id = nextAvailableOperatorId();
    const color = DEFAULT_COLORS[colorIndex % DEFAULT_COLORS.length];
    colorIndex++;
    scenario.operators[id] = {
        x, y, name: id, color, sequence: [],
    };
    snapOperatorToSlot(scenario.operators[id], x, y, id);
    return id;
}

function createBox(x, y, type) {
    const id   = type.toUpperCase() + "_" + nextBoxId++;
    const size = SIZES[type];

    const box = {
        x: x - size.w / 2,
        y: y - size.h / 2,
        w: size.w,
        h: size.h,
        type: type,
        name: id,
    };

    if (type === "swip") {
        box.has_part = false;
    } else if (type === "in") {
        box.start_count = 10;
    } else if (type === "out") {
        box.capacity = 50;
    }

    scenario.boxes[id] = box;
    return id;
}

function lineArtifactPlacement() {
    const stations = Object.values(scenario.stations);
    if (!stations.length) {
        // Center the entire blank-line composition, rather than using fixed
        // coordinates. The default arrow remains 875 × 85 canvas units.
        const gap = 25;
        const verticalGap = 35;
        const boxGap = 35;
        const groupWidth = SIZES.direction.w + gap + Math.max(SIZES.in.w, SIZES.out.w);
        const groupHeight = Math.max(
            verticalGap + SIZES.direction.h,
            SIZES.in.h + boxGap + SIZES.out.h
        );
        const centerX = (canvas.width - groupWidth) / 2;
        const centerY = (canvas.height - groupHeight) / 2;
        return {
            raw: {x: centerX + SIZES.direction.w + gap, y: centerY},
            direction: {x: centerX, y: centerY + verticalGap},
            finished: {x: centerX + SIZES.direction.w + gap,
                       y: centerY + SIZES.in.h + boxGap},
        };
    }
    // A generated C-shaped layout already has its own Incoming/Outgoing
    // positions. Add only a decorative arrow above the top station row,
    // without changing station locations or material-box coordinates.
    const minX = Math.min(...stations.map(s => s.x));
    const minY = Math.min(...stations.map(s => s.y));
    const maxX = Math.max(...stations.map(s => s.x + s.w));
    const anchorY = minY + (stations[0].h - SIZES.in.h) / 2;
    return {
        raw: {x: Math.max(20, minX - 140), y: anchorY},
        direction: {x: Math.max(20, minX), y: Math.max(20, minY - SIZES.direction.h - 25)},
        finished: {x: maxX + 50, y: anchorY},
    };
}

function ensureDefaultLineArtifacts() {
    const placement = lineArtifactPlacement();
    if (!Object.values(scenario.boxes).some(box => box.type === 'in')) {
        const id = createBox(placement.raw.x + SIZES.in.w / 2, placement.raw.y + SIZES.in.h / 2, 'in');
        scenario.boxes[id].name = 'Raw Material';
        scenario.boxes[id].start_count = 10;
    }
    if (!Object.values(scenario.boxes).some(box => box.type === 'direction')) {
        const id = createBox(placement.direction.x + SIZES.direction.w / 2, placement.direction.y + SIZES.direction.h / 2, 'direction');
        scenario.boxes[id].name = 'Line Direction';
        Object.assign(scenario.boxes[id], {rotation: 0, flip_horizontal: false, flip_vertical: false});
    }
    if (!Object.values(scenario.boxes).some(box => box.type === 'out')) {
        const id = createBox(placement.finished.x + SIZES.out.w / 2, placement.finished.y + SIZES.out.h / 2, 'out');
        scenario.boxes[id].name = 'Finished Goods';
        scenario.boxes[id].capacity = 50;
    }
}

// ============================================================
// PART 3b — Takt time tracking
// ============================================================
const taktTimeInput = document.getElementById("takt-time-input");

taktTimeInput.addEventListener("input", (e) => {
    e.target.value = e.target.value.replace(/[^0-9.]/g, "");
});

// ============================================================
// PART 4 — Canvas click handler (placement)
// ============================================================
function getCanvasMousePos(evt) {
    return view.worldPoint(evt);
}

canvas.addEventListener("click", (evt) => {
    if (view.isPanning || evt.shiftKey) return;
    if (dimensionTool) {
        const point=dimensionSnapPoint(getCanvasMousePos(evt));
        if(!dimensionStart) {
            dimensionStart=point;
            statusText.textContent='Dimension start set. Click the ending point.';
        } else if(Math.hypot(point.x-dimensionStart.x,point.y-dimensionStart.y)>0.001) {
            const id=`dim_${nextDimensionId++}`;
            scenario.dimensions[id]={x:dimensionStart.x,y:dimensionStart.y,
                x2:point.x,y2:point.y,start_anchor:dimensionStart.anchor,end_anchor:point.anchor,offset:-35};
            stopDimensionTool();
            setSelectedKeys([selectionKey('dimension',id)]);
            statusText.textContent=`Dimension ${id} added. Drag the blue line to change its offset; dotted extension lines keep it attached to the edges.`;
        }
        drawFrame();
        return;
    }
    if (!placingType) return;

    const pos = getCanvasMousePos(evt);

    if (placingType === "station") {
        createStation(pos.x, pos.y);
    } else if (placingType === "operator") {
        createOperator(pos.x, pos.y);
    } else {
        const id = createBox(pos.x, pos.y, placingType);
        if (placingType === 'direction') {
            Object.assign(scenario.boxes[id], {name: 'Line Direction',
                rotation: 0, flip_horizontal: false, flip_vertical: false});
            // Open the existing rotation/flip/resize controls immediately.
            setSelectedKeys([selectionKey('box', id)]);
        }
    }

    exitPlacementMode();
    statusText.textContent = `Added item. Drag it to reposition, or click another toolbar button to add more.`;
    drawFrame();
});

// ============================================================
// PART 5 — Drag + selection logic
// ============================================================
function findItemAtPosition(mx, my) {
    // A selected station reveals four independent resize handles.
    if(selectedItem?.type==='station' && selectedKeys.size===1) {
        const station=scenario.stations[selectedItem.id];
        const corner=station && hitStationCorner(station,{x:mx,y:my},view.scale);
        if(corner) return {type:'station-resize',id:selectedItem.id,pos:station,corner};
    }
    const dimension=dimensionAt({x:mx,y:my});
    if(dimension) return dimension;
    if (selectedItem?.type === 'box') {
        const selected = scenario.boxes[selectedItem.id];
        if (selected?.type === 'direction') {
            const handle = directionResizeHandle(selected);
            if (Math.hypot(mx - handle.x, my - handle.y) <= 11 / view.scale) {
                return {type: 'direction-resize', id: selectedItem.id, pos: selected};
            }
        }
    }
    // Operator circles take precedence if an old, freely positioned operator
    // overlaps a station rectangle.
    for (const id in scenario.operators) {
        const op = scenario.operators[id];
        if (Math.hypot(mx - op.x, my - op.y) <= OPERATOR_RADIUS + 4 / view.scale) {
            return {type: 'operator', id, pos: op};
        }
    }
    for (const id in scenario.stations) {
        const p = scenario.stations[id];
        if (mx >= p.x && mx <= p.x + p.w && my >= p.y && my <= p.y + p.h) {
            return { type: "station", id, pos: p };
        }
    }
    for (const id in scenario.boxes) {
        const p = scenario.boxes[id];
        if (p.type === 'direction'
            ? directionContainsPoint(p, mx, my, 4 / view.scale)
            : mx >= p.x && mx <= p.x + p.w && my >= p.y && my <= p.y + p.h) {
            return { type: "box", id, pos: p };
        }
    }
    return null;
}

canvas.addEventListener("mousedown", (evt) => {
    if (placingType || dimensionTool || view.isPanning || evt.button !== 0) return;
    smartGuideData = null;
    draggingWithoutSnap = evt.altKey;
    const mouse = getCanvasMousePos(evt);
    // An explicit sequence standing-point click must win over hit-testing the
    // operator sitting on that same snap circle. Apply on mouseup so dragging
    // the operator remains possible without changing a sequence assignment.
    const slot = !evt.ctrlKey && !evt.metaKey ? standingSlotAt(mouse) : null;
    if (slot) {
        pendingStandingClick = {slot, start:mouse};
        canvas.style.cursor = 'pointer';
        return;
    }
    const item = findItemAtPosition(mouse.x, mouse.y);
    const additive = evt.ctrlKey || evt.metaKey;

    if (item) {
        const key=selectionKey(item.type==='direction-resize'?'box':item.type==='station-resize'?'station':item.type==='dimension-endpoint'?'dimension':item.type,item.id);
        if (additive) {
            const next=new Set(selectedKeys);
            if (next.has(key)) next.delete(key); else next.add(key);
            setSelectedKeys(next);
            drawFrame();
            return;
        }
        if (['direction-resize','station-resize','dimension-endpoint'].includes(item.type)) {
            setSelectedKeys([key]);
            draggedItem=item;
        } else if (selectedKeys.size > 1 && selectedKeys.has(key)) {
            beginGroupDrag(mouse);
        } else {
            setSelectedKeys([key]);
            draggedItem=item;
        }
        if (draggedItem) {
            if(['station-resize','dimension-endpoint','dimension'].includes(item.type)) {
                dragStart={x:mouse.x,y:mouse.y,rect:{...item.pos},
                    points:item.type.startsWith('dimension')?dimensionPoints(item.pos):null,
                    offset:item.type==='dimension'?Number(item.pos.offset||0):null};
            }
            dragOffset.x = mouse.x-item.pos.x;
            dragOffset.y = mouse.y-item.pos.y;
            if(!['station-resize','dimension-endpoint','dimension'].includes(item.type))
                dragStart = {x:item.pos.x,y:item.pos.y};
        }
        canvas.style.cursor = ['direction-resize','station-resize'].includes(item.type)?'nwse-resize':item.type==='dimension-endpoint'?'crosshair':'grabbing';
    } else {
        // Drag from empty space to draw a marquee; Ctrl-drag adds to selection.
        marquee = {start:mouse,current:mouse,base:additive?new Set(selectedKeys):new Set()};
        if (!additive) setSelectedKeys([]);
        canvas.style.cursor='crosshair';
    }
    drawFrame();
});

canvas.addEventListener("mousemove", (evt) => {
    if (view.isPanning) return;
    const mouse=getCanvasMousePos(evt);
    if(dimensionTool) {
        if(dimensionStart) dimensionPreview=dimensionSnapPoint(mouse);
        drawFrame();
        return;
    }
    draggingWithoutSnap = evt.altKey;
    if (pendingStandingClick) {
        if (Math.hypot(mouse.x-pendingStandingClick.start.x,
                       mouse.y-pendingStandingClick.start.y) * view.scale < 6) return;
        const old = pendingStandingClick;
        pendingStandingClick = null;
        const item = findItemAtPosition(old.start.x, old.start.y);
        // Dragging an operator that shares its home snap circle with a
        // selectable sequence point still moves its home position.
        if (item?.type === 'operator' && item.id === selectedItem?.id) {
            draggedItem = item;
            dragStart = {x:item.pos.x, y:item.pos.y};
            dragOffset = {x:old.start.x-item.pos.x, y:old.start.y-item.pos.y};
        } else {
            canvas.style.cursor = 'default';
            return;
        }
    }
    if (marquee) {
        marquee.current=mouse;
        setSelectedKeys(new Set([...marquee.base,...hitSelection(rectFromPoints(marquee.start,mouse))]));
        drawFrame();
        return;
    }
    if (groupDrag) {
        moveGroup(mouse);
        drawFrame();
        return;
    }
    if (!draggedItem) {
        if (!placingType) {
            const item=findItemAtPosition(mouse.x,mouse.y);
            canvas.style.cursor=standingSlotAt(mouse)?'pointer':['station-resize','direction-resize'].includes(item?.type)?'nwse-resize':item?.type==='dimension-endpoint'?'crosshair':item?'grab':'default';
            return;
        }
        if (placingType==='station') {
            placementPreview=stationInsertPosition(scenario.stations,mouse.x,mouse.y,
                STATION_WIDTH,STATION_HEIGHT,view.scale);
            // Show live distances against existing items while previewing the new station.
            // Insertion itself remains controlled by stationInsertPosition
            // to avoid overlapping another station on click.
            const previewRect={x:placementPreview.x,y:placementPreview.y,
                w:STATION_WIDTH,h:STATION_HEIGHT};
            smartGuideData=smartSnapInput?.checked ? {rect:previewRect,guides:[],
                measurements:nearestGapMeasurements(previewRect,snapTargets())}:null;
        } else if (placingType==='operator') {
            placementPreview=nearestOperatorSlot(scenario.stations,scenario.operators,
                mouse.x,mouse.y,view.scale)||{x:mouse.x,y:mouse.y};
        } else return;
        drawFrame();
        return;
    }
    const newX=mouse.x-dragOffset.x, newY=mouse.y-dragOffset.y;
    if (draggedItem.type==='station-resize') {
        const sid=draggedItem.id;
        const original=dragStart.rect;
        const snap=guidePosition({x:mouse.x,y:mouse.y,w:0,h:0},new Set([selectionKey('station',sid)]));
        const rect=resizeStationRect(original,draggedItem.corner,{x:snap.x,y:snap.y});
        Object.assign(scenario.stations[sid],rect);
        updateAttachedOperators(scenario.stations,scenario.operators,sid);
        smartGuideData=smartSnapInput?.checked ? {...snap,rect,
            measurements:nearestGapMeasurements(rect,snapTargets(new Set([selectionKey('station',sid)])))}:null;
        const wField=document.getElementById('field-station-width');
        const hField=document.getElementById('field-station-height');
        const ppm=Number(scaleInput.value)||DEFAULT_PX_PER_M;
        if(wField)wField.value=(rect.w/ppm).toFixed(2);
        if(hField)hField.value=(rect.h/ppm).toFixed(2);
    } else if(draggedItem.type==='dimension-endpoint') {
        const d=scenario.dimensions[draggedItem.id];
        const point=dimensionSnapPoint(mouse);
        const first=draggedItem.which==='start';
        d[first?'x':'x2']=point.x;d[first?'y':'y2']=point.y;
        d[`${draggedItem.which}_anchor`]=point.anchor;
        updateDimensionPanel();
    } else if(draggedItem.type==='dimension') {
        const d=scenario.dimensions[draggedItem.id];
        // Only move the dimension LINE, never the measured object anchors.
        // Witness lines follow the anchors as stations move and resize.
        d.offset=dimensionOffsetFromDrag({...d,offset:dragStart.offset},dimensionBounds,
            {x:mouse.x-dragStart.x,y:mouse.y-dragStart.y});
        updateDimensionPanel();
    } else if (draggedItem.type==='direction-resize') {
        resizeDirectionFromPoint(draggedItem.pos,mouse.x,mouse.y);
        const wField=document.getElementById('field-direction-width');
        const hField=document.getElementById('field-direction-height');
        if(wField) wField.value=draggedItem.pos.w;
        if(hField) hField.value=draggedItem.pos.h;
    } else if (draggedItem.type==='operator') {
        const op=scenario.operators[draggedItem.id];
        if(dragStart && Math.hypot(newX-dragStart.x,newY-dragStart.y)*view.scale<5) return;
        // Station attachment takes precedence; free operators can align to
        // other canvas objects when no attachment point is close enough.
        const slot=nearestOperatorSlot(scenario.stations,scenario.operators,
            newX,newY,view.scale,draggedItem.id);
        if(slot) {
            snapOperatorToSlot(op,newX,newY,draggedItem.id);
            smartGuideData=smartSnapInput?.checked ? {
                rect:{x:op.x-OPERATOR_RADIUS,y:op.y-OPERATOR_RADIUS,
                    w:OPERATOR_RADIUS*2,h:OPERATOR_RADIUS*2},guides:[],
                measurements:[]}:null;
        } else {
            // Operator free movement stays exact: its station-attachment circles
            // are the only snapping targets for operators. Do not pull an
            // operator onto unrelated rectangular alignment anchors.
            op.x=newX;op.y=newY;
            delete op.attached_to;
            smartGuideData=smartSnapInput?.checked ? smartSnapRect(
                {x:op.x-OPERATOR_RADIUS,y:op.y-OPERATOR_RADIUS,
                 w:OPERATOR_RADIUS*2,h:OPERATOR_RADIUS*2},
                snapTargets(),view.scale,{snap:false}) : null;
        }
    } else if(draggedItem.type==='station') {
        moveStation(draggedItem.id,newX,newY);
    } else if(draggedItem.type==='box') {
        const b=draggedItem.pos;
        // Rotated line-direction bounding boxes do not start at b.x/b.y.
        const current=itemBounds(draggedItem);
        const offsetX=current.x-b.x,offsetY=current.y-b.y;
        const r=guidePosition({x:newX+offsetX,y:newY+offsetY,w:current.w,h:current.h},
            new Set([selectionKey('box',draggedItem.id)]));
        b.x=r.x-offsetX;b.y=r.y-offsetY;
    }
    drawFrame();
});

function finishCanvasPointer() {
    if (pendingStandingClick) {
        const {slot} = pendingStandingClick;
        pendingStandingClick = null;
        const editor = standingPointEditor;
        if (editor && validStandingStep(editor.operatorId,editor.stepIndex) &&
            scenario.operators[editor.operatorId].sequence[editor.stepIndex].loc === slot.stationId) {
            scenario.operators[editor.operatorId].sequence[editor.stepIndex].standing_side = slot.side;
            statusText.textContent = `Operator ${editor.operatorId}, step ${editor.stepIndex+1}: standing point set to ${slot.side} of S${slot.stationId}.`;
            renderSequenceList(scenario.operators[editor.operatorId]);
        }
    }
    const wasSelecting=!!marquee;
    marquee=null; groupDrag=null; draggedItem=null; dragStart=null;
    smartGuideData=null;
    if(wasSelecting) statusText.textContent=selectedKeys.size
        ? `${selectedKeys.size} item(s) selected. Drag any selected item to move them together; Ctrl-click to adjust selection.`
        : 'No items in that selection. Drag a rectangle around items to select them.';
    canvas.style.cursor=placingType||dimensionTool?'crosshair':'default';
    drawFrame();
}
canvas.addEventListener('mouseup',finishCanvasPointer);
canvas.addEventListener('mouseleave',()=>{
    // End active drag on leaving the canvas so movement cannot get stuck.
    if(pendingStandingClick) { pendingStandingClick=null; canvas.style.cursor='default'; }
    if(marquee||groupDrag||draggedItem) finishCanvasPointer();
    if(placementPreview){placementPreview=null;smartGuideData=null;drawFrame();}
});

// ============================================================
// PART 5b — Side panel (identity editing)
// ============================================================
const sidePanel     = document.getElementById("side-panel");
const panelTitle     = document.getElementById("panel-title");
const panelFields    = document.getElementById("panel-fields");
const deleteItemBtn  = document.getElementById("delete-item-btn");

function rgbToHex(rgbArr) {
    return "#" + rgbArr.map(v => v.toString(16).padStart(2, "0")).join("");
}

function hexToRgb(hex) {
    const bigint = parseInt(hex.slice(1), 16);
    return [(bigint >> 16) & 255, (bigint >> 8) & 255, bigint & 255];
}

// ============================================================
// PART 5c — Make the side panel draggable via its header bar
// ============================================================
const panelHeader = document.getElementById("panel-header");

let panelDrag = null; // {offsetX, offsetY}

panelHeader.addEventListener("mousedown", (evt) => {
    if (evt.target.closest('button')) return;
    const rect = sidePanel.getBoundingClientRect();
    panelDrag = {
        offsetX: evt.clientX - rect.left,
        offsetY: evt.clientY - rect.top,
    };
    // Switch from right-anchored to left/top-anchored so dragging works predictably
    sidePanel.style.right = "auto";
    sidePanel.style.left  = rect.left + "px";
    sidePanel.style.top   = rect.top + "px";
    evt.preventDefault();
});

document.addEventListener("mousemove", (evt) => {
    if (!panelDrag) return;
    sidePanel.style.left = (evt.clientX - panelDrag.offsetX) + "px";
    sidePanel.style.top  = (evt.clientY - panelDrag.offsetY) + "px";
});

document.addEventListener("mouseup", () => {
    panelDrag = null;
});
document.getElementById('panel-close').onclick = () => {
    setSelectedKeys([]);
    drawFrame();
};

// --------------------------------------------------------
// Build <option> list for a location dropdown, filtered by action
// --------------------------------------------------------
function buildLocationOptions(action, selectedLoc) {
    let options = `<option value="">-- select location --</option>`;

    if (action === "work") {
        for (const sid in scenario.stations) {
            const s = scenario.stations[sid];
            const sel = String(selectedLoc) === String(sid) ? "selected" : "";
            options += `<option value="${sid}" ${sel}>S${sid} — ${escapeHtml(s.name)}</option>`;
        }
    } else {
        for (const sid in scenario.stations) {
            const s = scenario.stations[sid];
            const sel = String(selectedLoc) === String(sid) ? "selected" : "";
            options += `<option value="${sid}" ${sel}>S${sid} — ${escapeHtml(s.name)}</option>`;
        }
        for (const bid in scenario.boxes) {
            const b = scenario.boxes[bid];
            if (b.type === 'direction') continue;
            const sel = String(selectedLoc) === String(bid) ? "selected" : "";
            options += `<option value="${bid}" ${sel}>${escapeHtml(b.name)} (${b.type.toUpperCase()})</option>`;
        }
    }

    return options;
}

// --------------------------------------------------------
function updateStationTotal(station) {
    const total = stationTotals(station);
    station.cycle_time = total.manual + total.auto;
}
function processOptions(step) {
    const processes = scenario.stations[step.loc]?.processes || [];
    return '<option value="">-- select process --</option>' + processes.map(p =>
        `<option value="${escapeHtml(p.id)}" ${p.id === step.process ? 'selected' : ''}>${escapeHtml(p.name)} (M ${p.manual_time} / A ${p.auto_time} min)</option>`).join('');
}
function selectDefaultProcess(step) {
    if (step.action === 'work') {
        const processes = scenario.stations[step.loc]?.processes || [];
        step.process = processes.length === 1 ? processes[0].id : '';
    } else delete step.process;
}

// Render the ordered list of sequence steps for an operator
// --------------------------------------------------------
function renderSequenceList(op) {
    if (selectedItem?.type === 'operator') syncStandingPointEditor(selectedItem.id);
    const container = document.getElementById("sequence-list");
    if (!container) return;

    if (op.sequence.length === 0) {
        container.innerHTML = `<p style="color:#888; font-size:12px;">No steps yet. Click "+ Add Step" below.</p>`;
        return;
    }

    let html = "";
    op.sequence.forEach((step, i) => {
        html += `
            <div class="sequence-step" data-builder-sequence="${i}" style="margin-bottom:8px; background:#fff; padding:6px; border:1px solid #ccc; border-radius:4px;">
              <div style="display:flex; gap:4px; align-items:center;">
                <span style="font-size:11px; color:#888; width:16px;">${i + 1}.</span>
                <select class="step-action" data-idx="${i}" style="flex:0 0 70px; font-size:11px;">
                    <option value="pick" ${step.action === "pick" ? "selected" : ""}>Pick</option>
                    <option value="work" ${step.action === "work" ? "selected" : ""}>Work</option>
                    <option value="drop" ${step.action === "drop" ? "selected" : ""}>Drop</option>
                </select>
                <select class="step-loc" data-idx="${i}" style="flex:1; font-size:11px; min-width:0;">
                    ${buildLocationOptions(step.action, step.loc)}
                </select>
                ${dragHandle('builder-sequence',String(i),'work step '+(i+1))}
                <button class="step-remove" data-idx="${i}" style="padding:2px 6px; background:#fde8e8;">✕</button>
              </div>
              ${scenario.stations[step.loc] ? `
                <div style="display:flex; align-items:center; flex-wrap:wrap; gap:5px; margin-top:6px; font-size:11px;">
                  <span><strong>Standing:</strong> ${step.standing_side ? escapeHtml(step.standing_side[0].toUpperCase()+step.standing_side.slice(1)) : 'Auto (nearest side)'}</span>
                  <button type="button" class="step-standing-select" data-idx="${i}"
                    aria-pressed="${standingPointEditor?.operatorId === selectedItem?.id && standingPointEditor?.stepIndex === i}"
                    style="font-size:11px; padding:3px 6px; border:1px solid #4777ae; background:${standingPointEditor?.operatorId === selectedItem?.id && standingPointEditor?.stepIndex === i ? '#dbeafe' : '#ffffff'};">
                    ${standingPointEditor?.operatorId === selectedItem?.id && standingPointEditor?.stepIndex === i ? '● Selecting on canvas' : '◎ Select on canvas'}
                  </button>
                  ${step.standing_side ? `<button type="button" class="step-standing-auto" data-idx="${i}" style="font-size:11px; padding:3px 6px;">Use Auto</button>` : ''}
                </div>` : ''}
              ${step.action === 'work' ? `<label style="font-size:11px;">Process
                  <select class="step-process" data-idx="${i}" style="width:100%; font-size:12px;">${processOptions(step)}</select>
                </label>` : ''}
            </div>
        `;
    });
    container.innerHTML = html;

    container.querySelectorAll(".step-action").forEach(sel => {
        sel.addEventListener("change", (e) => {
            const idx = parseInt(e.target.getAttribute("data-idx"));
            op.sequence[idx].action = e.target.value;
            op.sequence[idx].loc = "";
            delete op.sequence[idx].standing_side;
            selectDefaultProcess(op.sequence[idx]);
            renderSequenceList(op);
            drawFrame();
        });
    });

    container.querySelectorAll(".step-loc").forEach(sel => {
        sel.addEventListener("change", (e) => {
            const idx = parseInt(e.target.getAttribute("data-idx"));
            op.sequence[idx].loc = e.target.value;
            delete op.sequence[idx].standing_side;
            selectDefaultProcess(op.sequence[idx]);
            renderSequenceList(op);
            drawFrame();
        });
    });
    container.querySelectorAll('.step-standing-select').forEach(button => {
        button.onclick = e => {
            standingPointEditor = {operatorId:selectedItem.id, stepIndex:Number(e.currentTarget.dataset.idx)};
            renderSequenceList(op);
            statusText.textContent = `Choose one of the four dotted circles around S${op.sequence[standingPointEditor.stepIndex].loc} for step ${standingPointEditor.stepIndex+1}.`;
            drawFrame();
        };
    });
    container.querySelectorAll('.step-standing-auto').forEach(button => {
        button.onclick = e => {
            delete op.sequence[Number(e.currentTarget.dataset.idx)].standing_side;
            renderSequenceList(op);
            drawFrame();
        };
    });
    container.querySelectorAll('.step-process').forEach(select => {
        select.onchange = e => { op.sequence[Number(e.target.dataset.idx)].process = e.target.value; };
    });

    container.querySelectorAll(".step-remove").forEach(btn => {
        btn.addEventListener("click", (e) => {
            const idx = parseInt(e.target.getAttribute("data-idx"));
            op.sequence.splice(idx, 1);
            renderSequenceList(op);
            drawFrame();
        });
    });
}

// --------------------------------------------------------
// Change IDs and remap all operator references simultaneously (including swaps).
function changeStationId(oldId, newId) {
    oldId = String(oldId);
    newId = String(newId).trim();
    if (!/^[1-9][0-9]*$/.test(newId) || !Number.isSafeInteger(Number(newId))) {
        statusText.textContent = 'Station ID must be a positive whole number.';
        return false;
    }
    if (oldId === newId) return true;
    const original = scenario.stations[oldId];
    if (!original) return false;
    const displaced = scenario.stations[newId];
    scenario.stations[newId] = original;
    if (displaced) scenario.stations[oldId] = displaced;
    else delete scenario.stations[oldId];
    Object.values(scenario.operators).forEach(op => {
        (op.sequence || []).forEach(step => {
            const loc = String(step.loc);
            if (loc === oldId) step.loc = newId;
            else if (displaced && loc === newId) step.loc = oldId;
        });
    });
    remapOperatorAttachments(scenario.operators,
        displaced ? {[oldId]: newId, [newId]: oldId} : {[oldId]: newId});
    remapDimensionAnchors(displaced ? {[oldId]:newId,[newId]:oldId} : {[oldId]:newId});
    // Keep selected ID pointers consistent with station renumbering/swaps.
    const remapped=[...selectedKeys].map(key => key===selectionKey('station',oldId)
        ? selectionKey('station',newId) : displaced && key===selectionKey('station',newId)
            ? selectionKey('station',oldId) : key);
    selectedKeys.clear();remapped.forEach(key=>selectedKeys.add(key));
    nextStationId = Math.max(nextStationId, Number(newId) + 1);
    if (selectedItem?.type === 'station') {
        if (String(selectedItem.id) === oldId) selectedItem.id = newId;
        else if (displaced && String(selectedItem.id) === newId) selectedItem.id = oldId;
    }
    if (draggedItem?.type === 'station') draggedItem = null;
    statusText.textContent = displaced ? `Swapped S${oldId} and S${newId}. Operator sequences updated.` : `Renumbered S${oldId} to S${newId}. Operator sequences updated.`;
    openSidePanel(selectedItem);
    drawFrame();
    return true;
}

function renderStationProcesses(station, stationId) {
    const container = document.getElementById('process-list');
    if (!container) return;
    container.innerHTML = station.processes.map((p, i) => `
        <div class="process-editor" data-builder-process="${p.id}">
            <label>Process ${i + 1}</label>
            <input class="process-name" data-idx="${i}" value="${escapeHtml(p.name)}" aria-label="Process ${i + 1} name">
            <div class="process-time-row">
                <label>Manual (min)<input class="process-manual" data-idx="${i}" type="number" min="0" step="any" value="${p.manual_time}"></label>
                <label>Auto (min)<input class="process-auto" data-idx="${i}" type="number" min="0" step="any" value="${p.auto_time}"></label>
            </div>
            <div class="process-buttons">
                ${dragHandle('builder-process',p.id,p.name)}
                <button class="process-remove" data-idx="${i}" ${station.processes.length === 1 ? 'disabled' : ''}>Remove</button>
            </div>
        </div>`).join('');
    function refreshTotal() {
        updateStationTotal(station);
        const totals = stationTotals(station);
        document.getElementById('station-total').textContent = `Totals: manual ${Number(totals.manual.toFixed(3))}, auto ${Number(totals.auto.toFixed(3))} min`;
        drawFrame();
    }
    container.querySelectorAll('.process-name').forEach(input => input.oninput = e => {
        station.processes[Number(e.target.dataset.idx)].name = e.target.value;
    });
    for (const [selector, key] of [['.process-manual', 'manual_time'], ['.process-auto', 'auto_time']]) {
        container.querySelectorAll(selector).forEach(input => input.oninput = e => {
            const value = Number(e.target.value);
            station.processes[Number(e.target.dataset.idx)][key] = e.target.value !== '' && Number.isFinite(value) ? value : null;
            refreshTotal();
        });
    }
    container.querySelectorAll('.process-remove').forEach(button => button.onclick = () => {
        const index = Number(button.dataset.idx), process = station.processes[index];
        const references = Object.values(scenario.operators).flatMap(op => op.sequence || []).filter(step => String(step.loc) === String(stationId) && step.action === 'work' && step.process === process.id);
        if (references.length && !confirm(`Remove "${process.name}"? ${references.length} Work step(s) will need another process selected.`)) return;
        references.forEach(step => { step.process = ''; });
        station.processes.splice(index, 1);
        renderStationProcesses(station, stationId);
    });
    refreshTotal();
}

// Reorder stations over the existing ID slots and remap every reference once.
function reorderStations(id,beforeId) {
    const slots=Object.keys(scenario.stations).sort((a,b)=>Number(a)-Number(b));
    const ordered=[...slots];moveBefore(ordered,id,beforeId,item=>item);
    const original={...scenario.stations},mapping=Object.fromEntries(ordered.map((old,index)=>[old,slots[index]]));
    ordered.forEach((old,index)=>{scenario.stations[slots[index]]=original[old];});
    Object.values(scenario.operators).forEach(op=>(op.sequence||[]).forEach(step=>{if(Object.hasOwn(mapping,String(step.loc)))step.loc=mapping[String(step.loc)];}));
    remapOperatorAttachments(scenario.operators, mapping);
    remapDimensionAnchors(mapping);
    const remapped=[...selectedKeys].map(key=>key.startsWith('station:')
        ? selectionKey('station',mapping[key.slice(8)]||key.slice(8)):key);
    selectedKeys.clear();remapped.forEach(key=>selectedKeys.add(key));
    if(selectedItem?.type==='station')selectedItem.id=mapping[String(selectedItem.id)];
    draggedItem=null;openSidePanel(selectedItem);drawFrame();statusText.textContent='Station order updated. Operator references follow each station.';return mapping[id];
}
installDrag(panelFields,{
    source(node){
        const type=node.dataset.dragType,id=node.dataset.dragId;
        if(type==='builder-station')return {type,id,label:'Station S'+id};
        if(type==='builder-process'&&selectedItem?.type==='station')return {type,id,label:scenario.stations[selectedItem.id].processes.find(p=>p.id===id).name};
        if(type==='builder-sequence'&&selectedItem?.type==='operator')return {type,id,label:'Work step '+(Number(id)+1)};
        return null;
    },
    target(hit,event,data){
        const selector={'builder-station':'[data-builder-station]','builder-process':'[data-builder-process]','builder-sequence':'[data-builder-sequence]'}[data.type];
        const row=hit.closest(selector);if(!row)return null;
        return {...rowDrop(row,event.clientY),id:row.dataset.builderStation||row.dataset.builderProcess||row.dataset.builderSequence};
    },
    drop(data,where){
        if(data.type==='builder-station'){const list=Object.keys(scenario.stations).sort((a,b)=>Number(a)-Number(b));reorderStations(data.id,beforeFromDrop(list,where.id,where.after,id=>id));}
        else if(data.type==='builder-process'){const station=scenario.stations[selectedItem.id];moveBefore(station.processes,data.id,beforeFromDrop(station.processes,where.id,where.after));renderStationProcesses(station,selectedItem.id);}
        else{const op=scenario.operators[selectedItem.id];const list=op.sequence.map((_,index)=>({id:String(index)}));const before=beforeFromDrop(list,where.id,where.after);if(before===data.id)return;const [step]=op.sequence.splice(Number(data.id),1);let index=before===null?op.sequence.length:Number(before);if(before!==null&&Number(data.id)<index)index--;op.sequence.splice(index,0,step);renderSequenceList(op);}
    },
    keyboard(data,key){
        const direction=['ArrowUp','ArrowLeft'].includes(key)?-1:1;
        const list=data.type==='builder-station'?Object.keys(scenario.stations).sort((a,b)=>Number(a)-Number(b)):data.type==='builder-process'?scenario.stations[selectedItem.id].processes:scenario.operators[selectedItem.id].sequence;
        const index=data.type==='builder-station'?list.indexOf(data.id):data.type==='builder-process'?list.findIndex(p=>p.id===data.id):Number(data.id),other=index+direction;
        if(other<0||other>=list.length)return;
        let focusId=data.id;
        if(data.type==='builder-station'){focusId=reorderStations(data.id,direction<0?list[other]:list[other+1]||null);}
        else{[list[index],list[other]]=[list[other],list[index]];if(data.type==='builder-process')renderStationProcesses(scenario.stations[selectedItem.id],selectedItem.id);else renderSequenceList(scenario.operators[selectedItem.id]);}
        panelFields.querySelector(`[data-drag-type="${data.type}"][data-drag-id="${data.type==='builder-sequence'?other:focusId}"]`)?.focus();
    }
});

// Open the side panel for a selected item
// --------------------------------------------------------
function openSidePanel(item) {
    if (!item) {
        sidePanel.style.display = "none";
        return;
    }
    sidePanel.style.display = "block";

    if (item.type === 'dimension') {
        const d=scenario.dimensions[item.id];
        panelTitle.textContent='Dimension';
        panelFields.innerHTML=`<p style="font-size:12px;">Measured length: <strong id="field-dimension-length"></strong></p>
            <p style="font-size:12px;">Endpoints snap anywhere along station and box edges. Drag the blue dimension line to offset it; dotted extension lines connect the line to the measured edges without detaching its anchors.</p>
            <p style="font-size:11px;color:#506177;">If anchored to an object, the measurement follows its position and size. Scale (px/m) controls the length displayed.</p>`;
        updateDimensionPanel();
    } else if (item.type === "station") {
        const s = scenario.stations[item.id];
        panelTitle.textContent = `Station S${item.id}`;
        const orderOpen=document.getElementById('station-order-details')?.open||false;
        const stationIds = Object.keys(scenario.stations).sort((a, b) => Number(a) - Number(b));
        const index = stationIds.indexOf(String(item.id));
        panelFields.innerHTML = `
            <label for="field-station-id">Station ID</label>
            <div style="display:flex; gap:6px; margin-bottom:8px;">
                <input type="number" min="1" step="1" id="field-station-id" value="${item.id}" style="width:70px;">
                <button type="button" id="station-id-apply">Apply</button>
                            </div>
            <p style="font-size:11px; margin-bottom:10px;">An existing ID swaps stations. Operator sequences follow each station.</p>
            <details id="station-order-details" ${orderOpen?'open':''}><summary style="font-size:12px; cursor:pointer;">Drag to reorder station IDs</summary><ol class="station-order-list">${stationIds.map(id=>`<li data-builder-station="${id}">${dragHandle('builder-station',id,'station '+id)}<span>S${id} · ${escapeHtml(scenario.stations[id].name)}</span></li>`).join('')}</ol></details>
            <label>Name</label>
            <input type="text" id="field-name" value="${escapeHtml(s.name)}" style="width:100%; margin-bottom:8px;">
            <div style="display:flex;gap:10px;margin:10px 0;">
                <label style="flex:1;">Width (m)<input id="field-station-width" type="number" min="0.01" step="0.01" value="${(s.w/(Number(scaleInput.value)||DEFAULT_PX_PER_M)).toFixed(2)}" style="width:100%;"></label>
                <label style="flex:1;">Height (m)<input id="field-station-height" type="number" min="0.01" step="0.01" value="${(s.h/(Number(scaleInput.value)||DEFAULT_PX_PER_M)).toFixed(2)}" style="width:100%;"></label>
            </div>
            <p style="font-size:11px;color:#506177;margin:0 0 8px;">Drag a selected station's corner to resize. The opposite corner stays fixed. Dimensions follow the current px/m scale.</p>
            <h4 style="margin:8px 0;">Processes</h4>
            <p style="font-size:11px; margin-bottom:8px;">Manual time requires the operator. Auto time runs after manual time; the operator can leave. Choose each process in a Work step.</p>
            <div id="process-list"></div>
            <button id="add-process-btn" style="padding:6px; width:100%;">+ Add Process</button>
            <p id="station-total" style="font-size:12px; margin:8px 0;"></p>
            <label style="display:flex; align-items:center; gap:6px;">
                <input type="checkbox" id="field-haspart" ${s.has_part ? "checked" : ""}>
                Starts with a part
            </label>
        `;
        document.getElementById('station-id-apply').onclick = () => changeStationId(item.id, document.getElementById('field-station-id').value);
        document.getElementById('field-station-id').onkeydown = e => {
            if (e.key === 'Enter') { e.preventDefault(); document.getElementById('station-id-apply').click(); }
        };
        document.getElementById("field-name").addEventListener("input", (e) => {
            s.name = e.target.value;
            drawFrame();
        });
        for(const [field,key,min] of [['field-station-width','w',MIN_STATION_WIDTH],['field-station-height','h',MIN_STATION_HEIGHT]]) {
            document.getElementById(field).addEventListener('change',evt=>{
                const ppm=Number(scaleInput.value)||DEFAULT_PX_PER_M;
                const meters=Number(evt.target.value);
                if(Number.isFinite(meters)&&meters>0) s[key]=Math.max(min,meters*ppm);
                evt.target.value=(s[key]/ppm).toFixed(2);
                updateAttachedOperators(scenario.stations,scenario.operators,item.id);
                drawFrame();
            });
        }
        if (!s.processes) s.processes = stationProcesses(s);
        renderStationProcesses(s, item.id);
        document.getElementById('add-process-btn').onclick = () => {
            const currentMax = s.processes.reduce((max, p) => Math.max(max, Number(p.id.replace(/^p/, '')) || 0), 0);
            const next = Math.max(currentMax + 1, s.next_process_id || 1);
            s.next_process_id = next + 1;
            s.processes.push({id: 'p' + next, name: 'Process ' + next, manual_time: 1, auto_time: 0});
            renderStationProcesses(s, item.id);
        };
        document.getElementById("field-haspart").addEventListener("change", (e) => {
            s.has_part = e.target.checked;
            drawFrame();
        });

    } else if (item.type === "operator") {
        const op = scenario.operators[item.id];
        panelTitle.textContent = item.id;
        panelFields.innerHTML = `
            <label>Operator ID</label>
            <p style="font-weight:600; margin:5px 0 10px;">${escapeHtml(item.id)}</p>
            <label>Color</label>
            <input type="color" id="field-color" value="${rgbToHex(op.color)}" style="width:100%; margin-bottom:12px;">
            <hr>
            <label>Sequence</label>
            <p style="font-size:11px; color:#45556a; margin:5px 0 9px;">
              Choose a station step, then click one of its four dotted circles on the canvas.
              Each step can use a different station side. IN, OUT and SWIP boxes use their center.
            </p>
            <div id="sequence-list" style="margin-bottom:8px;"></div>
            <button id="add-step-btn" style="width:100%; padding:6px; background:#e8eef8; border:2px solid #1e3c78;">+ Add Step</button>
        `;

        document.getElementById("field-color").addEventListener("input", (e) => {
            op.color = hexToRgb(e.target.value);
            drawFrame();
        });

        renderSequenceList(op);
        if (standingPointEditor) {
            const step = op.sequence[standingPointEditor.stepIndex];
            statusText.textContent = `Select a dotted circle around S${step.loc}, or choose another station step in the Sequence editor.`;
        }

        document.getElementById("add-step-btn").addEventListener("click", () => {
            op.sequence.push({ action: "pick", loc: "" });
            renderSequenceList(op);
            drawFrame();
        });

    } else if (item.type === "box") {
        const b = scenario.boxes[item.id];
        panelTitle.textContent = b.type === 'direction' ? 'Line Direction' : `${b.type.toUpperCase()} Box`;

        let extraFieldsHtml = "";
        if (b.type === 'direction') {
            extraFieldsHtml = `
                <p style="font-size:12px; color:#556;">Drag the image to move it. Drag its bottom-right square to resize, or use the values below.</p>
                <div style="display:flex; gap:10px; margin-bottom:10px;">
                    <label style="flex:1;">Width
                        <input id="field-direction-width" type="number" min="${DIRECTION_MIN_WIDTH}" step="1" value="${b.w}" style="width:100%;"></label>
                    <label style="flex:1;">Height
                        <input id="field-direction-height" type="number" min="${DIRECTION_MIN_HEIGHT}" step="1" value="${b.h}" style="width:100%;"></label>
                </div>
                <label for="field-direction-rotation">Rotation (degrees)</label>
                <input id="field-direction-rotation" type="number" step="1" value="${b.rotation ?? 0}" style="width:100%; margin-bottom:8px;">
                <div style="display:flex; gap:6px; margin-bottom:10px;">
                    <button type="button" id="rotate-direction-left" style="flex:1;">↶ 90°</button>
                    <button type="button" id="rotate-direction-right" style="flex:1;">↷ 90°</button>
                </div>
                <div style="display:flex; gap:6px; margin-bottom:8px;">
                    <button type="button" id="flip-direction-horizontal" style="flex:1;">Flip horizontal</button>
                    <button type="button" id="flip-direction-vertical" style="flex:1;">Flip vertical</button>
                </div>
                <p id="direction-flip-state" style="font-size:11px; color:#556; margin:0;"></p>
            `;
        } else if (b.type === "swip") {
            extraFieldsHtml = `
                <label style="display:flex; align-items:center; gap:6px;">
                    <input type="checkbox" id="field-haspart" ${b.has_part ? "checked" : ""}>
                    Starts with a part
                </label>
            `;
        } else if (b.type === "in") {
            extraFieldsHtml = `
                <label>Starting Parts (reservoir)</label>
                <input type="text" id="field-startcount" value="${b.start_count}" style="width:100%; margin-bottom:8px;">
            `;
        } else if (b.type === "out") {
            extraFieldsHtml = `
                <label>Capacity (hard cap)</label>
                <input type="text" id="field-capacity" value="${b.capacity}" style="width:100%; margin-bottom:8px;">
            `;
        }

        panelFields.innerHTML = `
            <label>Name</label>
            <input type="text" id="field-name" value="${escapeHtml(b.name)}" style="width:100%; margin-bottom:8px;">
            ${extraFieldsHtml}
        `;

        document.getElementById("field-name").addEventListener("input", (e) => {
            b.name = e.target.value;
            drawFrame();
        });

        if (b.type === 'direction') {
            const angleInput = document.getElementById('field-direction-rotation');
            const syncFlipState = () => {
                document.getElementById('direction-flip-state').textContent =
                    `Horizontal: ${b.flip_horizontal ? 'flipped' : 'normal'} · Vertical: ${b.flip_vertical ? 'flipped' : 'normal'}`;
            };
            for (const [dimension, minimum] of [['w', DIRECTION_MIN_WIDTH], ['h', DIRECTION_MIN_HEIGHT]]) {
                const field = document.getElementById(`field-direction-${dimension === 'w' ? 'width' : 'height'}`);
                field.addEventListener('change', () => {
                    const next = Number(field.value);
                    if (!Number.isFinite(next) || next < minimum) { field.value = b[dimension]; return; }
                    // Keep its center fixed as width/height change.
                    const diff = Math.round(next) - b[dimension];
                    b[dimension] += diff;
                    b[dimension === 'w' ? 'x' : 'y'] -= diff / 2;
                    field.value = b[dimension];
                    drawFrame();
                });
            }
            angleInput.addEventListener('change', () => {
                const angle = Number(angleInput.value);
                if (!Number.isFinite(angle)) { angleInput.value = b.rotation ?? 0; return; }
                b.rotation = ((angle % 360) + 360) % 360;
                angleInput.value = b.rotation;
                drawFrame();
            });
            for (const [button, shift] of [['rotate-direction-left', -90], ['rotate-direction-right', 90]]) {
                document.getElementById(button).onclick = () => {
                    b.rotation = ((((b.rotation || 0) + shift) % 360) + 360) % 360;
                    angleInput.value = b.rotation;
                    drawFrame();
                };
            }
            for (const [button, field] of [['flip-direction-horizontal', 'flip_horizontal'], ['flip-direction-vertical', 'flip_vertical']]) {
                document.getElementById(button).onclick = () => {
                    b[field] = !b[field];
                    syncFlipState();
                    drawFrame();
                };
            }
            syncFlipState();
        }
        if (b.type === "swip") {
            document.getElementById("field-haspart").addEventListener("change", (e) => {
                b.has_part = e.target.checked;
                drawFrame();
            });
        } else if (b.type === "in") {
            document.getElementById("field-startcount").addEventListener("input", (e) => {
                e.target.value = e.target.value.replace(/[^0-9]/g, "");
                b.start_count = parseInt(e.target.value) || 0;
                drawFrame();
            });
        } else if (b.type === "out") {
            document.getElementById("field-capacity").addEventListener("input", (e) => {
                e.target.value = e.target.value.replace(/[^0-9]/g, "");
                b.capacity = parseInt(e.target.value) || 1;
                drawFrame();
            });
        }
    }
}

deleteItemBtn.addEventListener("click", () => {
    const keys=[...selectedKeys];
    if (!keys.length) return;
    // Station removal detaches any operators anchored to it.
    for (const key of keys) {
        const item=itemForKey(key);
        if(item?.type==='station') {
            detachStationOperators(scenario.operators,item.id);
            releaseDeletedDimensionAnchors('station',item.id);
            delete scenario.stations[item.id];
        }
    }
    for (const key of keys) {
        const item=itemForKey(key);
        if(item?.type==='operator') delete scenario.operators[item.id];
        if(item?.type==='box'){releaseDeletedDimensionAnchors('box',item.id);delete scenario.boxes[item.id];}
        if(item?.type==='dimension') delete scenario.dimensions[item.id];
    }
    setSelectedKeys([]);
    drawFrame();
});

// ============================================================
// PART 6 — Drawing
// ============================================================
const BOX_COLORS = {
    swip: "#1e3c78",
    in:   "#32b432",
    out:  "#dc3232",
    direction: "#666666",
};

function drawFrame() {
    renderOperatorOrderList();
    updatePlanningReview();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.save();
    view.apply(ctx);

    // ---- draw boxes ----
    for (const id in scenario.boxes) {
        const b = scenario.boxes[id];
        const color = BOX_COLORS[b.type] || "#888888";

        if (b.type === 'direction') {
            drawDirection(ctx, b, lineDirectionImage, {
                selected: selectedKeys.has(selectionKey('box',id)) && selectedKeys.size === 1,
                viewScale: view.scale,
            });
            if(selectedKeys.size>1 && selectedKeys.has(selectionKey('box',id))) {
                const bounds=itemBounds({type:'box',id,pos:b});
                ctx.save(); ctx.strokeStyle='#0066ff';ctx.lineWidth=2/view.scale;
                ctx.setLineDash([4/view.scale,4/view.scale]);
                ctx.strokeRect(bounds.x-4/view.scale,bounds.y-4/view.scale,
                    bounds.w+8/view.scale,bounds.h+8/view.scale);
                ctx.restore();
            }
            continue;
        }

        ctx.fillStyle = "#ffffff";
        ctx.fillRect(b.x, b.y, b.w, b.h);

        ctx.strokeStyle = color;
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        ctx.strokeRect(b.x, b.y, b.w, b.h);
        ctx.setLineDash([]);

        ctx.fillStyle = color;
        ctx.font = "12px Arial";
        ctx.textAlign = "left";
        ctx.textBaseline = "top";
        ctx.fillText(b.name, b.x + 5, b.y + 5);

        ctx.textAlign = "center";
        ctx.font = "18px Arial";

        if (b.type === "swip") {
            ctx.fillStyle = b.has_part ? "#1e3c78" : "#aaaaaa";
            ctx.fillText(b.has_part ? "●" : "○", b.x + b.w / 2, b.y + b.h / 2 + 6);
            ctx.font = "10px Arial";
            ctx.fillStyle = "#888888";
            ctx.fillText(b.has_part ? "has part" : "empty", b.x + b.w / 2, b.y + b.h - 12);
        } else if (b.type === "in") {
            ctx.fillStyle = "#000000";
            ctx.fillText(b.start_count, b.x + b.w / 2, b.y + b.h / 2 + 6);
            ctx.font = "10px Arial";
            ctx.fillStyle = "#888888";
            ctx.fillText("reservoir", b.x + b.w / 2, b.y + b.h - 12);
        } else if (b.type === "out") {
            ctx.fillStyle = "#000000";
            ctx.fillText(`0 / ${b.capacity}`, b.x + b.w / 2, b.y + b.h / 2 + 6);
            ctx.font = "10px Arial";
            ctx.fillStyle = "#888888";
            ctx.fillText("capacity", b.x + b.w / 2, b.y + b.h - 12);
        }

        ctx.textAlign = "left";
        ctx.textBaseline = "alphabetic";

        if (selectedKeys.has(selectionKey('box',id))) {
            ctx.strokeStyle = "#0066ff";
            ctx.lineWidth = 3;
            ctx.setLineDash([4, 4]);
            ctx.strokeRect(b.x - 5, b.y - 5, b.w + 10, b.h + 10);
            ctx.setLineDash([]);
        }
    }

    // ---- draw stations ----
    for (const id in scenario.stations) {
        const s = scenario.stations[id];

        ctx.fillStyle = "#c8c8c8";
        ctx.fillRect(s.x, s.y, s.w, s.h);

        ctx.fillStyle = "#000000";
        ctx.font = "11px Arial";
        ctx.textAlign = "left";
        ctx.textBaseline = "top";
        drawStationText(ctx, id, s);

        if (s.has_part) {
            ctx.fillStyle = "#1e3c78";
            ctx.beginPath();
            ctx.arc(s.x + s.w - 10, s.y + 10, 5, 0, Math.PI * 2);
            ctx.fill();
        }

        if (selectedKeys.has(selectionKey('station',id))) {
            ctx.strokeStyle = "#0066ff";
            ctx.lineWidth = 3;
            ctx.setLineDash([4, 4]);
            ctx.strokeRect(s.x - 5, s.y - 5, s.w + 10, s.h + 10);
            ctx.setLineDash([]);
        }
    }

    // Available *home attachment* rings appear only during operator placement
    // or drag, not when simply selecting an operator or a station.
    if (placingType === 'operator' || draggedItem?.type === 'operator') {
        const slots = operatorSlots(scenario.stations, scenario.operators,
            draggedItem?.type === 'operator' ? draggedItem.id : null);
        ctx.save();
        ctx.lineWidth = 1.6 / view.scale;
        ctx.strokeStyle = '#52799b';
        ctx.setLineDash([3 / view.scale, 4 / view.scale]);
        for (const slot of slots) {
            ctx.beginPath();
            ctx.arc(slot.x, slot.y, OPERATOR_RADIUS, 0, Math.PI * 2);
            ctx.stroke();
        }
        ctx.restore();
    }

    // Four clickable standing-point rings, ONLY around the station referenced
    // by the active sequence step. Multiple stations are edited independently.
    const standingSlots = activeStandingSlots();
    if (standingSlots.length) {
        const op = scenario.operators[selectedItem.id];
        ctx.save();
        ctx.lineWidth = 2 / view.scale;
        ctx.strokeStyle = `rgb(${op.color.join(',')})`;
        ctx.fillStyle = `rgba(${op.color.join(',')}, 0.20)`;
        ctx.setLineDash([4 / view.scale, 4 / view.scale]);
        for (const slot of standingSlots) {
            ctx.beginPath();
            ctx.arc(slot.x, slot.y, OPERATOR_RADIUS, 0, Math.PI * 2);
            if (slot.selected) ctx.fill();
            ctx.stroke();
            if (slot.selected) {
                ctx.setLineDash([]);
                ctx.beginPath(); ctx.arc(slot.x,slot.y,4 / view.scale,0,Math.PI*2);
                ctx.fillStyle = `rgb(${op.color.join(',')})`;
                ctx.fill();
                ctx.fillStyle = `rgba(${op.color.join(',')}, 0.20)`;
                ctx.setLineDash([4 / view.scale, 4 / view.scale]);
            }
        }
        ctx.restore();
    }

    // Preview new station/attached operator without creating saved items.
    if (placementPreview && placingType) {
        ctx.save();
        ctx.strokeStyle = '#1686c1'; ctx.lineWidth = 2 / view.scale;
        ctx.setLineDash([5 / view.scale, 4 / view.scale]);
        if (placingType === 'station') {
            ctx.fillStyle = 'rgba(22,134,193,0.10)';
            ctx.fillRect(placementPreview.x, placementPreview.y, STATION_WIDTH, STATION_HEIGHT);
            ctx.strokeRect(placementPreview.x, placementPreview.y, STATION_WIDTH, STATION_HEIGHT);
        } else if (placingType === 'operator') {
            ctx.beginPath(); ctx.arc(placementPreview.x, placementPreview.y, OPERATOR_RADIUS, 0, Math.PI*2);
            ctx.stroke();
        }
        ctx.restore();
    }

    // Selected station can be resized from any corner. Live width/height
    // measurements use the same physical scale as walking-time calculations.
    if(selectedItem?.type==='station' && selectedKeys.size===1) {
        const station=scenario.stations[selectedItem.id];
        if(station) {
            drawStationDimensions(ctx,station,Number(scaleInput.value)||DEFAULT_PX_PER_M,view.scale);
            drawStationHandles(ctx,station,view.scale);
        }
    }

    // ---- draw operators ----
    for (const id in scenario.operators) {
        const op = scenario.operators[id];
        const [r, g, b2] = op.color;

        ctx.fillStyle = `rgb(${r}, ${g}, ${b2})`;
        ctx.beginPath();
        ctx.arc(op.x, op.y, OPERATOR_RADIUS, 0, Math.PI * 2);
        ctx.fill();

        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.fillStyle = "#ffffff";
        ctx.font = "11px Arial";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(id, op.x, op.y);
        ctx.textAlign = "left";
        ctx.textBaseline = "alphabetic";

        if (selectedKeys.has(selectionKey('operator',id))) {
            ctx.strokeStyle = "#0066ff";
            ctx.lineWidth = 3;
            ctx.setLineDash([4, 4]);
            ctx.beginPath();
            ctx.arc(op.x, op.y, 24, 0, Math.PI * 2);
            ctx.stroke();
            ctx.setLineDash([]);
        }
    }
    // Saved dimensions remain visible outside measure mode, and recompute
    // anchored endpoints whenever their station or box moves/resizes.
    for(const [id,d] of Object.entries(scenario.dimensions)) {
        drawDimension(ctx,d,dimensionBounds,Number(scaleInput.value)||DEFAULT_PX_PER_M,
            view.scale,{selected:selectedKeys.has(selectionKey('dimension',id))});
    }
    if(dimensionTool && dimensionStart) {
        const end=dimensionPreview||dimensionStart;
        drawDimension(ctx,{x:dimensionStart.x,y:dimensionStart.y,x2:end.x,y2:end.y,offset:-35},
            dimensionBounds,Number(scaleInput.value)||DEFAULT_PX_PER_M,view.scale,{preview:true});
    }
    // Draw alignment and measurement overlays above objects, without
    // changing any operator/station drawing or storing the guides.
    drawSmartGuides(ctx, smartGuideData, Number(scaleInput.value)||DEFAULT_PX_PER_M, view.scale);
    if (marquee) {
        const area=rectFromPoints(marquee.start,marquee.current);
        ctx.save();
        ctx.fillStyle='rgba(0,102,255,0.10)';
        ctx.fillRect(area.x,area.y,area.w,area.h);
        ctx.strokeStyle='#0066ff';
        ctx.lineWidth=1.5/view.scale;
        ctx.setLineDash([5/view.scale,4/view.scale]);
        ctx.strokeRect(area.x,area.y,area.w,area.h);
        ctx.restore();
    }
    ctx.restore();
}

// ============================================================
// PART 7 — Save / Load full scenario
// ============================================================
function serializeScenario() {
    return {
        ...scenarioExtras,
        schema_version: schemaVersion,
        takt_time: Number(taktTimeInput.value),
        layout_scale_px_per_m: Number(scaleInput.value),
        walking_speed_m_per_s: Number(walkSpeedInput.value),
        stations:  scenario.stations,
        operators: Object.fromEntries(Object.entries(scenario.operators).map(
            ([id, op]) => [id, {...op, name: id}])),
        boxes:     scenario.boxes,
        dimensions: scenario.dimensions,
    };
}

// ---- Builder-only editing history and internal object clipboard ----
// A checkpoint captures the state BEFORE a user operation. Identical checkpoints
// are skipped by undo, so selecting an item does not waste an undo step.
const undoStack=[];
const redoStack=[];
const MAX_UNDO=80;
let objectClipboard=null;
let pasteGeneration=0;
let redoBaseline=null;
function editorSnapshot() {return JSON.stringify(serializeScenario());}
function recordUndo() {
    const current=editorSnapshot();
    if(undoStack.at(-1)!==current) {
        undoStack.push(current);
        if(undoStack.length>MAX_UNDO) undoStack.shift();
    }
    // Selecting an item should not discard redo history. If the last
    // checkpoint has changed since an undo, the next redo will reject it.
}
function restoreEditorSnapshot(json) {
    const data=JSON.parse(json);
    const keys=['stations','operators','boxes','dimensions'];
    for(const key of keys) {
        for(const id of Object.keys(scenario[key])) delete scenario[key][id];
        Object.assign(scenario[key],data[key]||{});
    }
    for (const [id,op] of Object.entries(scenario.operators)) op.name = id;
    scenarioExtras=Object.fromEntries(Object.entries(data).filter(([key]) =>
        !['schema_version','takt_time','layout_scale_px_per_m','walking_speed_m_per_s',...keys].includes(key)));
    taktTimeInput.value=String(data.takt_time??30);
    scaleInput.value=String(data.layout_scale_px_per_m??DEFAULT_PX_PER_M);
    walkSpeedInput.value=String(data.walking_speed_m_per_s??DEFAULT_WALK_M_PER_S);
    nextStationId=Math.max(nextStationId,1,...Object.keys(scenario.stations).map(id=>Number(id)+1||1));
    nextBoxId=Math.max(nextBoxId,1,...Object.keys(scenario.boxes).map(id=>Number(id.split('_').at(-1))+1||1));
    nextDimensionId=Math.max(nextDimensionId,1,...Object.keys(scenario.dimensions).map(id=>Number(id.replace(/^dim_/,''))+1||1));
    for(const id of Object.keys(scenario.stations)) updateAttachedOperators(scenario.stations,scenario.operators,id);
    setSelectedKeys([]); draggedItem=null; groupDrag=null; marquee=null;
    dimensionStart=null;dimensionPreview=null; smartGuideData=null;
    exitPlacementMode();stopDimensionTool();
    drawFrame();rememberDraft();
}
function undoEditor() {
    const current=editorSnapshot();
    if(redoStack.length && redoBaseline!==null && current!==redoBaseline) redoStack.length=0;
    while(undoStack.length) {
        const prior=undoStack.pop();
        if(prior===current) continue;
        redoStack.push(current);redoBaseline=prior;
        restoreEditorSnapshot(prior);
        statusText.textContent='Undo: last canvas edit restored.';
        return true;
    }
    statusText.textContent='Nothing to undo.';
    return false;
}
function redoEditor() {
    const current=editorSnapshot();
    if(redoStack.length && redoBaseline!==null && current!==redoBaseline) {
        redoStack.length=0;statusText.textContent='Redo unavailable after new edits.';return false;
    }
    while(redoStack.length) {
        const next=redoStack.pop();
        if(next===current) continue;
        undoStack.push(current);redoBaseline=next;
        restoreEditorSnapshot(next);
        statusText.textContent='Redo: edit restored.';
        return true;
    }
    statusText.textContent='Nothing to redo.';
    return false;
}
function copyCanvasSelection() {
    const items=[...selectedKeys].map(itemForKey).filter(Boolean);
    if(!items.length) return false;
    objectClipboard=items.map(item=>({type:item.type,id:item.id,
        pos:structuredClone(item.pos),
        endpoints:item.type==='dimension'?dimensionPoints(item.pos):null}));
    pasteGeneration=0;
    statusText.textContent=`Copied ${items.length} canvas item(s). Press Ctrl+V to paste.`;
    return true;
}
function pasteCanvasSelection() {
    if(!objectClipboard?.length) return false;
    recordUndo();
    redoStack.length=0;
    const shift=35*(++pasteGeneration), mappings={station:{},box:{},operator:{},dimension:{}};
    const staged=[];
    // Insert stations/boxes first to build reference maps for the operators/rulers.
    for(const type of ['station','box','operator','dimension']) {
        for(const item of objectClipboard.filter(i=>i.type===type)) {
            const data=structuredClone(item.pos);
            data.x+=shift;data.y+=shift;
            if(type==='dimension') {data.x2+=shift;data.y2+=shift;}
            let id;
            if(type==='station') {
                do {id=String(nextStationId++);} while(scenario.stations[id]);
                scenario.stations[id]=data;
            } else if(type==='box') {
                do {id=`${String(data.type).toUpperCase()}_${nextBoxId++}`;} while(scenario.boxes[id]);
                scenario.boxes[id]=data;
            } else if(type==='operator') {
                id=nextAvailableOperatorId();
                data.name=id;
                scenario.operators[id]=data;
            } else {
                do {id=`dim_${nextDimensionId++}`;} while(scenario.dimensions[id]);
                scenario.dimensions[id]=data;
            }
            mappings[type][item.id]=id;
            staged.push({type,id,data,source:item});
        }
    }
    for(const {type,data,source} of staged) {
        if(type==='operator') {
            const anchor=data.attached_to;
            if(anchor) {
                if(mappings.station[anchor.station_id])
                    anchor.station_id=mappings.station[anchor.station_id];
                else delete data.attached_to;
            }
            for(const step of data.sequence||[]) {
                if(mappings.station[step.loc]) step.loc=mappings.station[step.loc];
                if(mappings.box[step.loc]) step.loc=mappings.box[step.loc];
            }
        } else if(type==='dimension') {
            for(const which of ['start','end']) {
                const a=data[`${which}_anchor`];
                if(!a) continue;
                const newId=mappings[a.type]?.[a.id];
                if(newId) a.id=newId;
                else {
                    const original=source.endpoints[which];
                    data[which==='start'?'x':'x2']=original.x+shift;
                    data[which==='start'?'y':'y2']=original.y+shift;
                    data[`${which}_anchor`]=null;
                }
            }
        }
    }
    for(const {type,id} of staged) if(type==='station')
        updateAttachedOperators(scenario.stations,scenario.operators,id);
    setSelectedKeys(staged.map(item=>selectionKey(item.type,item.id)));
    drawFrame();
    statusText.textContent=`Pasted ${staged.length} item(s), offset ${shift} canvas units.`;
    return true;
}
// Capture BEFORE handlers mutate the scenario. Text fields retain native
// copy/paste/undo; canvas shortcuts act only when the user is not typing.
const isTextEditing=(element)=>!!element?.closest?.('input,textarea,select,[contenteditable="true"],[role="textbox"]');
document.addEventListener('mousedown',evt=>{
    if(evt.button===0 && !isTextEditing(evt.target) &&
        (evt.target===canvas || evt.target.closest?.('#toolbar,#toolbar2,#panel-fields,#delete-item-btn')))
        recordUndo();
},true);
document.addEventListener('focusin',evt=>{
    if(isTextEditing(evt.target) && evt.target.closest?.('#side-panel,#toolbar2')) recordUndo();
},true);
document.addEventListener('input',evt=>{
    if(evt.target.closest?.('#side-panel,#toolbar2')) recordUndo();
},true);
document.addEventListener('keydown',evt=>{
    const modifier=(evt.ctrlKey||evt.metaKey)&&!evt.altKey;
    if(!modifier || isTextEditing(evt.target)) return;
    const key=evt.key.toLowerCase();
    if(key==='z') {evt.preventDefault();evt.stopPropagation();evt.shiftKey?redoEditor():undoEditor();}
    else if(key==='y') {evt.preventDefault();evt.stopPropagation();redoEditor();}
    else if(key==='c' && selectedKeys.size) {evt.preventDefault();copyCanvasSelection();}
    else if(key==='v' && objectClipboard?.length) {evt.preventDefault();pasteCanvasSelection();}
},true);

function applyLoadedScenario(data) {
    undoStack.length=0;redoStack.length=0;redoBaseline=null;
    freshLineSnapshot = null;
    if (data.schema_version !== schemaVersion) throw new Error('Scenario must be migrated by the server before opening.');
    scenarioExtras = Object.fromEntries(Object.entries(data).filter(([key]) =>
        !['schema_version', 'takt_time', 'layout_scale_px_per_m', 'walking_speed_m_per_s', 'stations', 'operators', 'boxes', 'dimensions'].includes(key)));
    for (const k in scenario.stations)  delete scenario.stations[k];
    for (const k in scenario.operators) delete scenario.operators[k];
    for (const k in scenario.boxes)     delete scenario.boxes[k];
    for (const k in scenario.dimensions) delete scenario.dimensions[k];

    Object.assign(scenario.stations,  data.stations  || {});
    Object.assign(scenario.operators, data.operators || {});
    for (const [id,op] of Object.entries(scenario.operators)) op.name = id;
    Object.assign(scenario.boxes,     data.boxes     || {});
    Object.assign(scenario.dimensions, data.dimensions || {});
    // Older scenarios without attached_to remain free-floating, with original
    // coordinates/sizes untouched. Attached operators use their side anchor.
    Object.keys(scenario.stations).forEach(id =>
        updateAttachedOperators(scenario.stations, scenario.operators, id));

    Object.values(scenario.stations).forEach(updateStationTotal);
    taktTimeInput.value = data.takt_time || 30;
    scaleInput.value = data.layout_scale_px_per_m ?? DEFAULT_PX_PER_M;
    walkSpeedInput.value = data.walking_speed_m_per_s ?? DEFAULT_WALK_M_PER_S;

    nextStationId = nextBoxId = nextDimensionId = 1;
    stopDimensionTool();
    draggedItem = null;
    dragStart = null;
    pendingStandingClick = null;
    exitPlacementMode();
    Object.keys(scenario.stations).forEach(sid => {
        const n = parseInt(sid, 10);
        if (!isNaN(n) && n >= nextStationId) nextStationId = n + 1;
    });
    Object.keys(scenario.dimensions).forEach(id=>{
        const n=Number(id.replace(/^dim_/,''));
        if(Number.isInteger(n)&&n>=nextDimensionId) nextDimensionId=n+1;
    });
    Object.keys(scenario.boxes).forEach(bid => {
        const parts = bid.split("_");
        const n = parseInt(parts[parts.length - 1], 10);
        if (!isNaN(n) && n >= nextBoxId) nextBoxId = n + 1;
    });

    setSelectedKeys([]);
    marquee=null;groupDrag=null;
    view.reset();
    drawFrame();
    restorePlanningReview();
}

function rememberDraft() {
    try {
        sessionStorage.setItem(DRAFT_KEY, JSON.stringify({ scenario: serializeScenario(), loadedFilename, loadedRevision, lastSavedSnapshot, suggestedFilename }));
    } catch (err) { console.warn('Could not keep the builder draft:', err); }
}
function reviewCore() {
    const data=serializeScenario();
    return JSON.stringify(Object.fromEntries(['schema_version','takt_time','stations','operators','boxes'].map(key=>[key,data[key]])));
}
function updatePlanningReview() {
    const required=scenarioExtras.planning_origin?.material_review_required===true;
    const panel=document.getElementById('planning-review-panel');panel.hidden=!required;
    if(!required)return;
    const reviewed=reviewSnapshot!==null&&reviewSnapshot===reviewCore();
    panel.classList.toggle('builder-review--complete',reviewed);
    document.getElementById('planning-review-heading').textContent=reviewed?'Generated line · setup reviewed':'Generated line · material-flow review required';
    document.getElementById('planning-review-state').textContent=reviewed?'Current setup checked. Changes to the layout, timings, inventory or work sequence require another review.':'Complete the material setup, then check it before running. Work-only drafts need deliveries or starting parts.';
}
async function restorePlanningReview() {
    reviewSnapshot=null;updatePlanningReview();const token=++reviewRequest;
    if(scenarioExtras.planning_origin?.material_review_required!==true)return;
    const snapshot=reviewCore();
    try{const data=await postJson('/builder-setup/api/review-status',{scenario:serializeScenario()});if(token===reviewRequest&&snapshot===reviewCore()&&data.reviewed){reviewSnapshot=snapshot;updatePlanningReview();}}
    catch{ /* The review button reports validation errors for incomplete drafts. */ }
}
document.getElementById('planning-review-button').onclick=async()=>{
    const button=document.getElementById('planning-review-button');button.disabled=true;
    const snapshot=reviewCore();
    try{const data=await postJson('/builder-setup/api/review',{scenario:serializeScenario()});
        if(snapshot!==reviewCore())throw new Error('The setup changed during the check. Review the current version again.');
        scenarioExtras.planning_origin=data.scenario.planning_origin;reviewSnapshot=reviewCore();updatePlanningReview();rememberDraft();statusText.textContent='Setup reviewed. Run Simulation to check actual machine and material flow.';
    }catch(error){reviewSnapshot=null;updatePlanningReview();statusText.textContent='Review incomplete: '+error.message;}
    finally{button.disabled=false;}
};
for(const event of ['input','change','click'])document.addEventListener(event,()=>queueMicrotask(updatePlanningReview));
async function applyPlanningHandoff() {
    const pending=JSON.parse(sessionStorage.getItem(HANDOFF_KEY)||'null');
    if(!pending?.scenario)return;
    document.getElementById('planning-handoff-notice').hidden=false;
    const result=await postJson('/import-scenario',{scenario:pending.scenario});
    const hasItems=Object.values(scenario).some(items=>Object.keys(items).length>0)||taktTimeInput.value!=='30';
    if(hasItems&&isCurrentUnsaved()&&!confirm('Open the generated line as a new draft and replace your unsaved builder changes? Save or export your current work first if you want to keep it.')){
        statusText.textContent='Generated draft not opened. Your current builder changes are kept.';return;
    }
    applyLoadedScenario(result.scenario);ensureDefaultLineArtifacts();loadedFilename=loadedRevision=lastSavedSnapshot=null;
    suggestedFilename=pending.suggestedFilename||'generated_line.json';rememberDraft();sessionStorage.removeItem(HANDOFF_KEY);
    document.getElementById('planning-handoff-notice').hidden=true;statusText.textContent='Opened a new generated line draft. Review material movement before simulation; Save Scenario creates a new file or version.';
}
document.getElementById('apply-planning-handoff').onclick=async()=>{try{await applyPlanningHandoff();}catch(error){statusText.textContent='Generated draft could not open: '+error.message;}};
document.getElementById('dismiss-planning-handoff').onclick=()=>{sessionStorage.removeItem(HANDOFF_KEY);document.getElementById('planning-handoff-notice').hidden=true;};

function chooseSaveMode(filename) {
    return new Promise(resolve => {
        const dialog = document.getElementById('save-dialog');
        document.getElementById('save-dialog-message').textContent = `Save changes to "${filename}" or keep it and create a numbered version?`;
        const finish = mode => { dialog.close(); resolve(mode); };
        document.getElementById('save-overwrite-btn').onclick = () => finish('overwrite');
        document.getElementById('save-duplicate-btn').onclick = () => finish('duplicate');
        document.getElementById('save-cancel-btn').onclick = () => finish(null);
        dialog.oncancel = e => { e.preventDefault(); finish(null); };
        dialog.showModal();
    });
}
document.getElementById('save-scenario-btn').addEventListener('click', async () => {
    const button = document.getElementById('save-scenario-btn');
    button.disabled = true;
    try {
        let filename = loadedFilename;
        let name = null;
        let mode = 'create';
        if (filename) {
            mode = await chooseSaveMode(filename);
            if (!mode) return;
        } else {
            name = prompt('Enter a name for this scenario:', suggestedFilename.replace(/\.json$/i, ''));
            if (!name?.trim()) return;
        }
        const snapshot = JSON.parse(JSON.stringify(serializeScenario()));
        async function submit() {
            const res = await fetch('/save-scenario', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, filename, mode, scenario: snapshot,
                    expected_revision: filename === loadedFilename ? loadedRevision : null }),
            });
            return res.json();
        }
        let data = await submit();
        if (data.status === 'exists') {
            filename = data.filename;
            mode = await chooseSaveMode(filename);
            if (!mode) return;
            data = await submit();
        }
        if (data.status !== 'saved') throw new Error(data.error || 'Could not save scenario.');
        loadedFilename = data.filename;
        suggestedFilename = data.filename;
        loadedRevision = data.revision;
        lastSavedSnapshot = JSON.stringify(snapshot);
        rememberDraft();
        statusText.textContent = `Saved "${loadedFilename}"`;
        await refreshScenarioList();
    } catch (err) {
        statusText.textContent = err.message || 'Could not reach the server to save.';
    } finally { button.disabled = false; }
});

function refreshScenarioList(selectedFilename = loadedFilename) {
    return fetch("/list-scenarios")
        .then(res => res.json())
        .then(data => {
            const select = document.getElementById("scenario-select");
            select.innerHTML = '<option value="">-- Select a saved scenario --</option>';
            data.files.forEach(filename => {
                const label = filename.replace(".json", "").replace(/_/g, " ");
                const opt = document.createElement("option");
                opt.value = filename;
                opt.textContent = label;
                select.appendChild(opt);
            });
            if (selectedFilename && data.files.includes(selectedFilename)) select.value = selectedFilename;
        })
        .catch(err => console.error("Error listing scenarios:", err));
}

// Rename a persisted scenario without saving unsaved edits or changing the canvas.
document.getElementById('rename-scenario-btn').addEventListener('click', async () => {
    const button = document.getElementById('rename-scenario-btn');
    const selected = document.getElementById('scenario-select').value;
    if (!selected) {
        statusText.textContent = 'Select a saved scenario to rename first.';
        return;
    }
    const input = prompt('Rename saved scenario (without .json):', selected.replace(/\.json$/i, '').replace(/_/g, ' '));
    if (input === null) return;
    if (!input.trim()) {
        statusText.textContent = 'Please enter a non-empty scenario name.';
        return;
    }
    button.disabled = true;
    try {
        // The loaded scenario carries a revision for optimistic-concurrency
        // protection. Other selected files get their current revision from SQL.
        let revision = selected === loadedFilename ? loadedRevision : null;
        if (!revision) {
            const current = await requestJson('/load-scenario/' + encodeURIComponent(selected));
            if (!current.found) throw new Error('This scenario no longer exists. Refresh your saved scenarios.');
            revision = current.revision || null;
        }
        const result = await postJson('/rename-scenario', {
            filename: selected, new_name: input.trim(), expected_revision: revision,
        });
        if (result.status !== 'renamed') throw new Error(result.error || 'Could not rename scenario.');
        if (selected === loadedFilename) {
            loadedFilename = result.filename;
            loadedRevision = result.revision;
            suggestedFilename = result.filename;
            // lastSavedSnapshot intentionally stays unchanged: any unsaved
            // canvas edits remain unsaved after the database record is renamed.
            rememberDraft();
        }
        await refreshScenarioList(result.filename);
        statusText.textContent = `Renamed "${selected}" to "${result.filename}". Unsaved canvas changes were not saved.`;
    } catch (error) {
        statusText.textContent = 'Rename failed: ' + (error.message || 'Unknown error.');
    } finally {
        button.disabled = false;
    }
});

document.getElementById("load-scenario-btn").addEventListener("click", () => {
    const filename = document.getElementById("scenario-select").value;
    if (!filename) {
        statusText.textContent = "Please select a scenario to load.";
        setTimeout(() => { statusText.textContent = ""; }, 2000);
        return;
    }

    const current = JSON.stringify(serializeScenario());
    const hasItems = Object.values(scenario).some(items => Object.keys(items).length > 0) || taktTimeInput.value !== '30';
    if (hasItems && isCurrentUnsaved() && !confirm('Replace your unsaved builder changes with the selected scenario?')) return;
    requestJson("/load-scenario/" + encodeURIComponent(filename))
        .then(data => {
            if (data.found) {
                applyLoadedScenario(data.scenario);
                loadedFilename = data.filename || filename;
                suggestedFilename = loadedFilename;
                loadedRevision = data.revision || null;
                lastSavedSnapshot = JSON.stringify(serializeScenario());
                rememberDraft();
                statusText.textContent = `Loaded "${filename.replace(".json", "")}"`;
                setTimeout(() => { statusText.textContent = ""; }, 2000);
            } else {
                statusText.textContent = "Scenario file not found.";
                setTimeout(() => { statusText.textContent = ""; }, 2000);
            }
        })
        .catch(err => { statusText.textContent = err.message; });
});
// ============================================================
// PART 7b — Run scenario simulation
// ============================================================
const runScenarioBtn = document.getElementById("run-scenario-btn");

runScenarioBtn.addEventListener("click", () => {
    runScenarioBtn.disabled = true;
    runScenarioBtn.textContent = "Running...";

    fetch("/launch", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(serializeScenario()),
    })
    .then(res => res.json().then(data => ({ status: res.status, body: data })))
    .then(({ status, body }) => {
        runScenarioBtn.disabled = false;
        runScenarioBtn.textContent = "▶ Run Simulation";

        if (status !== 200) {
            if (body.status === "invalid") {
                alert("Scenario has errors:\n\n" + body.errors.join("\n"));
            } else if (body.status === "runtime_error") {
                alert("Simulation failed at runtime:\n\n" + body.error);
            } else {
                alert("Unexpected error running scenario.");
            }
            return;
        }

        rememberDraft();
        window.location.href = "/simulate";
    })
    .catch(err => {
        runScenarioBtn.disabled = false;
        runScenarioBtn.textContent = "▶ Run Simulation";
        console.error("Error launching scenario:", err);
        alert("Could not reach the server. Check the console for details.");
    });
});
// ============================================================
// PART 8 — New blank line + initialization
// ============================================================
function startNewLine({persistDraft = true} = {}) {
    undoStack.length=0;redoStack.length=0;redoBaseline=null;
    for (const key of ['stations', 'operators', 'boxes', 'dimensions']) {
        for (const id of Object.keys(scenario[key])) delete scenario[key][id];
    }
    scenarioExtras = {};
    loadedFilename = null;
    loadedRevision = null;
    lastSavedSnapshot = null;
    suggestedFilename = 'scenario.json';
    nextStationId = 1;
    nextBoxId = 1;
    nextDimensionId = 1;
    colorIndex = 0;
    reviewSnapshot = null;
    reviewRequest++;
    taktTimeInput.value = '30';
    scaleInput.value = String(DEFAULT_PX_PER_M);
    walkSpeedInput.value = String(DEFAULT_WALK_M_PER_S);
    draggedItem = null;
    dragStart = null;
    pendingStandingClick = null;
    setSelectedKeys([]);
    marquee=null;groupDrag=null;
    exitPlacementMode();
    stopDimensionTool();
    document.getElementById('scenario-select').value = '';
    sessionStorage.removeItem(HANDOFF_KEY);
    document.getElementById('planning-handoff-notice').hidden = true;
    ensureDefaultLineArtifacts();
    freshLineSnapshot = JSON.stringify(serializeScenario());
    view.reset();
    drawFrame();
    if (persistDraft) rememberDraft();
}

function isCurrentUnsaved() {
    const current = JSON.stringify(serializeScenario());
    return current !== lastSavedSnapshot && current !== freshLineSnapshot;
}

document.getElementById('new-line-btn').addEventListener('click', () => {
    if (isCurrentUnsaved() && !confirm('Create a new blank line? Unsaved changes to the current line will be discarded. Saved SQL scenarios will not be deleted.')) return;
    startNewLine();
    statusText.textContent = 'New blank line created with Raw Material, Line Direction and Finished Goods. Add stations and operators to begin.';
});

async function initBuilder() {
    const controls = [...document.querySelectorAll('button, input, select')];
    const disabled = controls.map(control => control.disabled);
    controls.forEach(control => { control.disabled = true; });
    try {
        const draft = JSON.parse(sessionStorage.getItem(DRAFT_KEY) || 'null');
        if (draft?.scenario) {
            const result = await postJson('/import-scenario', {scenario: draft.scenario});
            applyLoadedScenario(result.scenario);
            loadedFilename = draft.loadedFilename || null;
            loadedRevision = draft.loadedRevision || null;
            lastSavedSnapshot = draft.lastSavedSnapshot || null;
            suggestedFilename = draft.suggestedFilename || loadedFilename || 'scenario.json';
        } else {
            startNewLine({persistDraft: false});
        }
        if(new URLSearchParams(location.search).get('source')==='planning')await applyPlanningHandoff();
        else document.getElementById('planning-handoff-notice').hidden=!sessionStorage.getItem(HANDOFF_KEY);
    } catch (err) {
        statusText.textContent = 'Could not restore the previous draft: ' + err.message;
        const previous = sessionStorage.getItem(DRAFT_KEY);
        if (previous) sessionStorage.setItem(DRAFT_KEY + '-unrestored', previous);
    } finally {
        controls.forEach((control, index) => { control.disabled = disabled[index]; });
        document.body.dataset.builderReady = 'true';
    }
    window.addEventListener('pagehide', rememberDraft);
    await refreshScenarioList();
    drawFrame();
}

const importFile = document.getElementById('import-scenario-file');
document.getElementById('import-scenario-btn').addEventListener('click', () => importFile.click());
importFile.addEventListener('change', async () => {
    const file = importFile.files[0];
    if (!file) return;
    const button = document.getElementById('import-scenario-btn');
    button.disabled = true;
    try {
        let original;
        try { original = JSON.parse(await file.text()); }
        catch { throw new Error('This file is not valid JSON. Choose a scenario JSON file.'); }
        const result = await postJson('/import-scenario', {scenario: original});
        const current = JSON.stringify(serializeScenario());
        const hasItems = Object.values(scenario).some(items => Object.keys(items).length > 0) || taktTimeInput.value !== '30';
        if (hasItems && isCurrentUnsaved() && !confirm('Replace your unsaved builder changes with the imported scenario?')) return;
        applyLoadedScenario(result.scenario);
        loadedFilename = null;
        loadedRevision = null;
        lastSavedSnapshot = null;
        suggestedFilename = file.name;
        rememberDraft();
        statusText.textContent = `Imported "${file.name}"` + (result.migrated_from ? ` — upgraded from format v${result.migrated_from} to v${schemaVersion}.` : '.');
    } catch (err) {
        statusText.textContent = 'Import failed: ' + err.message;
    } finally {
        button.disabled = false;
        importFile.value = '';
    }
});

document.getElementById('export-scenario-btn').addEventListener('click', async () => {
    const button = document.getElementById('export-scenario-btn');
    button.disabled = true;
    try {
        const data = await postJson('/export-scenario', {scenario: serializeScenario(), filename: loadedFilename || suggestedFilename});
        const blob = new Blob([JSON.stringify(data, null, 2) + '\n'], {type: 'application/json'});
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = loadedFilename || suggestedFilename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        statusText.textContent = `Exported scenario in format v${schemaVersion}.`;
    } catch (err) {
        statusText.textContent = 'Export failed: ' + err.message;
    } finally { button.disabled = false; }
});

initBuilder();

// Guide visibility does not alter the saved layout. Changing scale updates the
// displayed meter values immediately, and simulation uses the same scale.
smartSnapInput?.addEventListener('change', () => {smartGuideData=null;drawFrame();});
scaleInput?.addEventListener('input', () => {
    updateDimensionPanel();
    if(selectedItem?.type==='station') {
        const station=scenario.stations[selectedItem.id];
        const ppm=Number(scaleInput.value)||DEFAULT_PX_PER_M;
        for(const [id,value] of [['field-station-width',station?.w],['field-station-height',station?.h]]) {
            const input=document.getElementById(id);
            if(input&&value) input.value=(value/ppm).toFixed(2);
        }
    }
    drawFrame();
});

// Selection is transient; Escape cancels it without editing the scenario.
document.addEventListener('keydown', evt => {
    if(evt.key!=='Escape') return;
    if(dimensionTool){stopDimensionTool();drawFrame();}
    else if(placingType) exitPlacementMode();
    else if(selectedKeys.size || marquee){marquee=null;groupDrag=null;setSelectedKeys([]);drawFrame();}
});
