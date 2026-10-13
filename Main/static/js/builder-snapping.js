// Pure, world-coordinate snapping functions. Screen-space tolerances are divided
// by viewport zoom so placement remains equally precise at any zoom level.
export const OPERATOR_RADIUS = 16;
export const OPERATOR_GAP = 10;
export const STATION_GAP = 22;
export const STATION_SNAP_PIXELS = 16;
export const OPERATOR_SNAP_PIXELS = 22;
export const SIDES = ['top', 'right', 'bottom', 'left'];

export function operatorPoint(station, side) {
    const distance = OPERATOR_RADIUS + OPERATOR_GAP;
    switch (side) {
        case 'top': return {x: station.x + station.w / 2, y: station.y - distance};
        case 'right': return {x: station.x + station.w + distance, y: station.y + station.h / 2};
        case 'bottom': return {x: station.x + station.w / 2, y: station.y + station.h + distance};
        case 'left': return {x: station.x - distance, y: station.y + station.h / 2};
        default: return null;
    }
}

export function operatorSlots(stations, operators, ignoreOperatorId = null) {
    const occupied = new Set();
    for (const [id, op] of Object.entries(operators)) {
        if (id === ignoreOperatorId || !op.attached_to) continue;
        occupied.add(`${op.attached_to.station_id}:${op.attached_to.side}`);
    }
    const slots = [];
    for (const [stationId, station] of Object.entries(stations)) {
        for (const side of SIDES) {
            if (occupied.has(`${stationId}:${side}`)) continue;
            slots.push({station_id: stationId, side, ...operatorPoint(station, side)});
        }
    }
    return slots;
}

export function nearestOperatorSlot(stations, operators, x, y, zoom = 1, ignoreOperatorId = null) {
    const limit = OPERATOR_SNAP_PIXELS / Math.max(0.01, zoom);
    let best = null;
    for (const slot of operatorSlots(stations, operators, ignoreOperatorId)) {
        const distance = Math.hypot(slot.x - x, slot.y - y);
        if (distance <= limit && (best === null || distance < best.distance)) best = {...slot, distance};
    }
    return best;
}

export function updateAttachedOperators(stations, operators, stationId) {
    for (const op of Object.values(operators)) {
        if (op.attached_to?.station_id !== String(stationId)) continue;
        const station = stations[stationId];
        const point = station && operatorPoint(station, op.attached_to.side);
        if (point) Object.assign(op, point);
        // Deletion is handled by detachStationOperators so the last location is preserved.
    }
}

export function detachStationOperators(operators, stationId) {
    for (const op of Object.values(operators)) {
        if (op.attached_to?.station_id === String(stationId)) delete op.attached_to;
    }
}

export function remapOperatorAttachments(operators, idMap) {
    // Snapshot original IDs first so swaps cannot accidentally map twice.
    for (const op of Object.values(operators)) {
        if (op.attached_to && Object.hasOwn(idMap, op.attached_to.station_id)) {
            op.attached_to.station_id = String(idMap[op.attached_to.station_id]);
        }
    }
}

const intersects = (a, b) => a.x < b.x + b.w && a.x + a.w > b.x &&
                            a.y < b.y + b.h && a.y + a.h > b.y;

// Align edges/centers or dock alongside an existing station with an air gap.
// Consider stations reasonably close along the perpendicular axis only.
export function snapStation(stations, ignoreId, x, y, width, height, zoom = 1) {
    const tolerance = STATION_SNAP_PIXELS / Math.max(0.01, zoom);
    let xBest = {value: x, diff: tolerance + 1};
    let yBest = {value: y, diff: tolerance + 1};
    for (const [id, other] of Object.entries(stations)) {
        if (id === String(ignoreId)) continue;
        const xNear = x < other.x + other.w + 160 && x + width > other.x - 160;
        const yNear = y < other.y + other.h + 130 && y + height > other.y - 130;
        if (yNear) {
            const choices = [other.x, other.x + other.w - width,
                other.x + (other.w - width) / 2,
                other.x - width - STATION_GAP, other.x + other.w + STATION_GAP];
            for (const candidate of choices) {
                const diff = Math.abs(x - candidate);
                if (diff <= tolerance && diff < xBest.diff) xBest = {value: candidate, diff};
            }
        }
        if (xNear) {
            const choices = [other.y, other.y + other.h - height,
                other.y + (other.h - height) / 2,
                other.y - height - STATION_GAP, other.y + other.h + STATION_GAP];
            for (const candidate of choices) {
                const diff = Math.abs(y - candidate);
                if (diff <= tolerance && diff < yBest.diff) yBest = {value: candidate, diff};
            }
        }
    }
    return {x: xBest.value, y: yBest.value, snappedX: xBest.diff <= tolerance, snappedY: yBest.diff <= tolerance};
}

// Do not create an exact overlapping duplicate when clicking on an existing
// station: insert in the nearest free neighbouring position instead.
export function stationInsertPosition(stations, centerX, centerY, width, height, zoom = 1) {
    const x = centerX - width / 2, y = centerY - height / 2;
    let result = snapStation(stations, null, x, y, width, height, zoom);
    const others = Object.values(stations);
    if (!others.some(s => intersects({...result, w:width, h:height}, s))) return result;
    const proposals = others.flatMap(s => [
        {x:s.x + s.w + STATION_GAP, y:s.y}, {x:s.x - width - STATION_GAP, y:s.y},
        {x:s.x, y:s.y + s.h + STATION_GAP}, {x:s.x, y:s.y - height - STATION_GAP}
    ]);
    const free = proposals.filter(p => !others.some(s => intersects({...p,w:width,h:height},s)));
    if (!free.length) return result;
    free.sort((a,b) => (a.x-x)**2+(a.y-y)**2 - ((b.x-x)**2+(b.y-y)**2));
    return {...free[0], snappedX:true, snappedY:true};
}
