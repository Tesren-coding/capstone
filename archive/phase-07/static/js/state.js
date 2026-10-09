// ============================================================
// state.js
// Tracks operator positions, part carrying, and event progression
// JavaScript equivalent of state.py
// ============================================================

function buildOperatorState(events, stationCenters, boxCenters, opNames,
                             opStartPart, incomingStart, packingStart) {

    const opEvents = {};
    opNames.forEach(op => {
        opEvents[op] = events.filter(e => e.operator === op);
    });

    function getLocCenter(loc) {
        if (loc === null || loc === undefined) return null;
        if (typeof loc === "number") {
            return stationCenters[loc] ? { ...stationCenters[loc] } : null;
        }
        if (boxCenters[loc]) return { ...boxCenters[loc] };
        return null;
    }

    function getStartCenter(op) {
        const firstEv = opEvents[op][0];
        const center  = getLocCenter(firstEv.loc);
        return center || { x: 100, y: 100 };
    }

    const opPositions       = {};
    const opTargets         = {};
    const opEventIndex      = {};
    const opHasPart         = {};
    const opDropoffTarget   = {};
    const opPendingDropoff  = {};
    const partPositions     = {};

    opNames.forEach(op => {
        const start = getStartCenter(op);
        opPositions[op]      = { x: start.x, y: start.y };
        opTargets[op]        = { x: start.x, y: start.y };
        opEventIndex[op]     = 0;
        opHasPart[op]        = !!opStartPart[op];
        opDropoffTarget[op]  = null;
        opPendingDropoff[op] = null;
        partPositions[op]    = opHasPart[op] ? { x: start.x, y: start.y } : null;
    });

    const opCycleLength = {};
    opNames.forEach(op => {
        let count = 0;
        for (const e of opEvents[op]) {
            count++;
            if (e.status === "idle") break;
        }
        opCycleLength[op] = count;
    });

    // parts sitting at stations/boxes, waiting to be picked up
    // key = station id (number) or box key (string), value = {x, y}
    const droppedParts = {};

    // counters for Incoming / Packing
    const counters = {
        incoming: incomingStart,
        packing:  packingStart,
    };

    return {
        opEvents,
        opPositions,
        opTargets,
        opEventIndex,
        opCycleLength,
        opHasPart,
        opDropoffTarget,
        opPendingDropoff,
        partPositions,
        droppedParts,
        counters,
        getLocCenter,
    };
}