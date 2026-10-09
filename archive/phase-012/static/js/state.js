// static/js/state.js
//
// Builds and updates operator/box state for simulate.html playback.
//
// Event schema (from simulation.py):
//   { time, operator, loc, status, part, reason?, from?, to? }
//   status ∈ "pickup" | "moving" | "dropoff" | "working" | "idle" | "blocked"
//
// Operators restart their sequence every takt cycle — this is already
// fully unrolled in the event log (simulation.py runs `while True` for
// ~100 takt cycles), so playback is pure timestamp-driven advancement.
// No cycle-length looping needed on the frontend.

function buildOperatorState(simEvents, stationCenters, boxCenters, opNames, scenario) {
  const locCenters = Object.assign({}, stationCenters, boxCenters);

  const opEvents      = {};
  const opEventIndex  = {};
  const opPositions   = {};
  const partPositions = {};
  const isBlocked     = {};
  const blockedReason = {};

  opNames.forEach(op => {
    const evList = simEvents
      .filter(e => e.operator === op)
      .sort((a, b) => a.time - b.time);

    opEvents[op]      = evList;
    opEventIndex[op]  = 0;
    isBlocked[op]     = false;
    blockedReason[op] = null;

    // "Home" = location of this operator's first sequence step —
    // they always restart there each takt cycle.
    const opDef = scenario.operators[op] || {};
    const seq   = opDef.sequence || [];
    let home = { x: 0, y: 0 };
    if (seq.length > 0 && locCenters[seq[0].loc]) {
      home = locCenters[seq[0].loc];
    }

    opPositions[op]   = { x: home.x, y: home.y };
    partPositions[op] = null;
  });

  // ---- initial station/box live state, mirrors simulation.py exactly ----
  const stationState = {};
  for (const sid in scenario.stations) {
    stationState[sid] = { hasPart: !!scenario.stations[sid].has_part };
  }

  const boxState = {};
  for (const bid in scenario.boxes) {
    const b = scenario.boxes[bid];
    if (b.type === "in") {
      boxState[bid] = { type: "in", remaining: b.start_count ?? 0 };
    } else if (b.type === "out") {
      boxState[bid] = { type: "out", count: 0 };
    } else if (b.type === "swip") {
      boxState[bid] = { type: "swip", has_part: !!b.has_part }; // snake_case — matches draw.js's drawBox
    }
  }

  return {
    opEvents,
    opEventIndex,
    opPositions,
    partPositions,
    isBlocked,
    blockedReason,
    stationState,
    boxState,
    droppedParts: {},
    _locCenters: locCenters,
  };
}

function updateOperators(opState, opNames, scenario, simClock, taktTime, taktResetCount, speed) {
  const absTime    = taktResetCount * taktTime + simClock;
  const locCenters = opState._locCenters;

  // ---- reset station/box live state to initial, then replay every
  //      event (across ALL operators) up to absTime. Occupancy is
  //      shared state, so it can't be computed per-operator alone. ----
  for (const sid in scenario.stations) {
    opState.stationState[sid].hasPart = !!scenario.stations[sid].has_part;
  }
  for (const bid in scenario.boxes) {
    const b  = scenario.boxes[bid];
    const st = opState.boxState[bid];
    if (b.type === "in")   st.remaining = b.start_count ?? 0;
    if (b.type === "out")  st.count = 0;
    if (b.type === "swip") st.has_part = !!b.has_part;
  }

  const allEvents = [];
  opNames.forEach(op => {
    for (const ev of opState.opEvents[op]) {
      if (ev.time <= absTime) allEvents.push(ev);
    }
  });
  allEvents.sort((a, b) => a.time - b.time);

  for (const ev of allEvents) {
    if (ev.status === "pickup") {
      if (opState.stationState[ev.loc]) {
        opState.stationState[ev.loc].hasPart = false;
      } else if (opState.boxState[ev.loc]) {
        const b = opState.boxState[ev.loc];
        if (b.type === "in")   b.remaining = Math.max(0, b.remaining - 1);
        if (b.type === "swip") b.has_part = false;
      }
    } else if (ev.status === "dropoff") {
      if (opState.stationState[ev.loc]) {
        opState.stationState[ev.loc].hasPart = true;
      } else if (opState.boxState[ev.loc]) {
        const b = opState.boxState[ev.loc];
        if (b.type === "out")  b.count = b.count + 1;
        if (b.type === "swip") b.has_part = true;
      }
    }
  }

  // ---- droppedParts: stations/swip boxes currently holding a resting part ----
  const droppedParts = {};
  for (const sid in opState.stationState) {
    if (opState.stationState[sid].hasPart && locCenters[sid]) {
      droppedParts[sid] = { x: locCenters[sid].x, y: locCenters[sid].y };
    }
  }
  for (const bid in opState.boxState) {
    const b = opState.boxState[bid];
    if (b.type === "swip" && b.has_part && locCenters[bid]) {
      droppedParts[bid] = { x: locCenters[bid].x, y: locCenters[bid].y };
    }
  }
  opState.droppedParts = droppedParts;

  // ---- per-operator: advance index, blocked-freeze fix, walk interpolation ----
  opNames.forEach(op => {
    const evList = opState.opEvents[op];
    if (!evList || evList.length === 0) return;

    let idx = opState.opEventIndex[op];
    while (idx < evList.length - 1 && evList[idx + 1].time <= absTime) {
      idx++;
    }

    const atEnd   = idx === evList.length - 1;
    const current = evList[idx];
    if (!current || current.time > absTime) return; // hasn't started yet

    if (atEnd && current.status === "blocked") {
      // --- Phase 11 fix: freeze in place, never loop back ---
      opState.isBlocked[op]     = true;
      opState.blockedReason[op] = current.reason || "blocked";
    } else {
      opState.isBlocked[op]     = false;
      opState.blockedReason[op] = null;
    }

    opState.opEventIndex[op] = idx;

    // "idle" events carry loc: null — keep last known target in that case.
    const target = current.loc ? locCenters[current.loc] : null;

    if (target) {
      const pos  = opState.opPositions[op];
      const dx   = target.x - pos.x;
      const dy   = target.y - pos.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist <= speed || dist === 0) {
        pos.x = target.x;
        pos.y = target.y;
      } else {
        pos.x += (dx / dist) * speed;
        pos.y += (dy / dist) * speed;
      }
    }

    opState.partPositions[op] = current.part
      ? { x: opState.opPositions[op].x, y: opState.opPositions[op].y }
      : null;
  });
}