// Replay the SimPy event stream so machine rules and visible playback agree.
export function buildOperatorState(events, stationCenters, boxCenters, opNames, scenario) {
    const state = {
        events, eventIndex: 0, time: 0, finished: false, stopReason: null,
        opPositions: {}, partPositions: {}, carrying: {}, phase: {}, moves: {},
        isBlocked: {}, blockedReason: {}, blockedLoc: {}, stationState: {},
        boxState: {}, droppedParts: {}, centers: {...stationCenters, ...boxCenters},
        traces: {},
    };
    for (const sid in scenario.stations) {
        state.stationState[sid] = {hasPart: !!scenario.stations[sid].has_part,
            busy: false, phase: 'idle', process: null, processName: null,
            operator: null, until: null};
    }
    for (const bid in scenario.boxes) {
        const box = scenario.boxes[bid];
        state.boxState[bid] = {type: box.type, remaining: box.start_count || 0,
            count: 0, has_part: !!box.has_part};
    }
    opNames.forEach(op => {
        const data = scenario.operators[op];
        state.opPositions[op] = {x: data.x, y: data.y};
        state.carrying[op] = false;
        state.phase[op] = 'ready';
        state.isBlocked[op] = false;
        state.traces[op] = [];
    });
    refreshPartPositions(state);
    return state;
}

function applySimulationEvent(state, event) {
    const op = event.operator, loc = event.loc;
    const machine = state.stationState[loc];
    const box = state.boxState[loc];
    switch (event.status) {
        case 'moving':
            state.moves[op] = {...event};
            state.phase[op] = 'walking';
            break;
        case 'arrived':
            state.opPositions[op] = {...event.position};
            delete state.moves[op];
            state.phase[op] = 'ready';
            break;
        case 'pickup':
            if (machine) machine.hasPart = false;
            else if (box.type === 'in') box.remaining--;
            else if (box.type === 'out') box.count--;
            else box.has_part = false;
            state.carrying[op] = true;
            state.phase[op] = 'ready';
            break;
        case 'dropoff':
            if (machine) machine.hasPart = true;
            else if (box.type === 'in') box.remaining++;
            else if (box.type === 'out') box.count++;
            else box.has_part = true;
            state.carrying[op] = false;
            state.phase[op] = 'ready';
            break;
        case 'manual_start':
            Object.assign(machine, {busy: true, phase: 'manual', process: event.process,
                processName: event.process_name, operator: op,
                until: event.time + event.duration + event.auto_time});
            state.phase[op] = 'working';
            break;
        case 'auto_start':
            Object.assign(machine, {busy: true, phase: 'automatic', until: event.time + event.duration});
            break;
        case 'operator_ready': state.phase[op] = 'ready'; break;
        case 'process_complete':
            Object.assign(machine, {busy: false, phase: 'idle', until: null, operator: null});
            break;
        case 'waiting': state.phase[op] = 'waiting'; break;
        case 'planned_wait_start': state.phase[op] = 'idle'; break;
        case 'planned_wait_end': state.phase[op] = 'ready'; break;
        case 'idle': state.phase[op] = 'idle'; break;
        case 'blocked':
            state.isBlocked[op] = true;
            state.blockedReason[op] = event.reason;
            state.blockedLoc[op] = loc;
            state.phase[op] = 'blocked';
            state.stopReason = event.reason;
            break;
        case 'simulation_complete': state.finished = true; break;
    }
}

function refreshPartPositions(state) {
    state.droppedParts = {};
    for (const sid in state.stationState) if (state.stationState[sid].hasPart) {
        const p = state.centers[sid];
        // Keep the icon below the ID rather than on top of the station name.
        state.droppedParts[sid] = {x: p.x + 42, y: p.y - 26};
    }
    for (const bid in state.boxState) if (state.boxState[bid].type === 'swip' && state.boxState[bid].has_part) {
        state.droppedParts[bid] = {...state.centers[bid]};
    }
    for (const op in state.opPositions) {
        const p = state.opPositions[op];
        state.partPositions[op] = state.carrying[op] ? {x: p.x + 14, y: p.y - 14} : null;
    }
}

function refreshOperatorTraces(state, targetTime) {
    const maxAge = 1.25;
    for (const op in state.opPositions) {
        const trace = state.traces[op] || (state.traces[op] = []);
        const point = state.opPositions[op];
        if (state.moves[op]) {
            const last = trace[trace.length - 1];
            if (!last || Math.hypot(last.x - point.x, last.y - point.y) >= 5) {
                trace.push({x: point.x, y: point.y, time: targetTime});
            } else {
                last.x = point.x;
                last.y = point.y;
                last.time = targetTime;
            }
        }
        state.traces[op] = trace.filter(sample => targetTime - sample.time <= maxAge);
    }
}

export function updateOperators(state, targetTime) {
    if (state.stopReason || state.finished) return;
    while (state.eventIndex < state.events.length && state.events[state.eventIndex].time <= targetTime + 1e-9) {
        const event = state.events[state.eventIndex++];
        applySimulationEvent(state, event);
        if (state.stopReason || state.finished) { targetTime = event.time; break; }
    }
    state.time = targetTime;
    for (const op in state.moves) {
        const move = state.moves[op];
        const fraction = Math.max(0, Math.min(1, (targetTime - move.time) / move.duration));
        state.opPositions[op] = {x: move.start.x + (move.end.x - move.start.x) * fraction,
            y: move.start.y + (move.end.y - move.start.y) * fraction};
    }
    refreshPartPositions(state);
    refreshOperatorTraces(state, targetTime);
}
