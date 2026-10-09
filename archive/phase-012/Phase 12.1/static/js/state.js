// static/js/state.js
//
// Visual choreography engine for simulate.html.
//
// Unlike the previous version, this does NOT derive operator position
// from the raw event log's timestamps (which log zero travel time between
// locations). Instead, each operator's own `sequence` (from the scenario)
// drives a self-paced walk → act → work loop, so parts visibly travel
// with the operator between pick and drop, instead of teleporting.
//
// Blocking is detected live: if a pick/drop can't succeed against the
// current shared box/station state, the operator freezes in place,
// matching backend semantics (mirrors can_pick_from/can_drop_to in
// simulation.py).
//
// KNOWN SIMPLIFICATION: the "idle" wait between takt cycles (backend:
// takt_time - time_used) is not yet replicated here — operators loop
// their sequence continuously. This means visual cycle count may run
// ahead of the banner's takt counter. Flagged as a fast-follow.

function buildOperatorState(simEvents, stationCenters, boxCenters, opNames, scenario) {
  const locCenters = Object.assign({}, stationCenters, boxCenters);

  const opState = {
    _locCenters: locCenters,
    sequence: {},
    seqIdx: {},
    phase: {},            // "walking" | "working"
    carrying: {},
    workStartAbsTime: {},
    opPositions: {},
    partPositions: {},
    isBlocked: {},
    blockedReason: {},
    droppedParts: {},
    stationState: {},
    boxState: {},
  };

  for (const sid in scenario.stations) {
    opState.stationState[sid] = { hasPart: !!scenario.stations[sid].has_part };
  }
  for (const bid in scenario.boxes) {
    const b = scenario.boxes[bid];
    if (b.type === "in")   opState.boxState[bid] = { type: "in", remaining: b.start_count ?? 0 };
    if (b.type === "out")  opState.boxState[bid] = { type: "out", count: 0 };
    if (b.type === "swip") opState.boxState[bid] = { type: "swip", has_part: !!b.has_part };
  }

  opNames.forEach(op => {
    const opDef = scenario.operators[op] || {};
    const seq   = opDef.sequence || [];

    opState.sequence[op]         = seq;
    opState.seqIdx[op]           = 0;
    opState.phase[op]            = "walking";
    opState.carrying[op]         = false;
    opState.workStartAbsTime[op] = null;
    opState.isBlocked[op]        = false;
    opState.blockedReason[op]    = null;

    const home = seq.length > 0 && locCenters[seq[0].loc] ? locCenters[seq[0].loc] : { x: 0, y: 0 };
    opState.opPositions[op]   = { x: home.x, y: home.y };
    opState.partPositions[op] = null;
  });

  return opState;
}

function canPick(loc, opState, scenario) {
  if (opState.stationState[loc]) return opState.stationState[loc].hasPart;
  const b = opState.boxState[loc];
  if (!b) return false;
  if (b.type === "in")   return b.remaining > 0;
  if (b.type === "swip") return b.has_part;
  return true;
}

function canDrop(loc, opState, scenario) {
  if (opState.stationState[loc]) return true;
  const b = opState.boxState[loc];
  if (!b) return true;
  if (b.type === "out") {
    const capacity = (scenario.boxes[loc] || {}).capacity ?? Infinity;
    return b.count < capacity;
  }
  return true;
}

function doPick(loc, opState) {
  if (opState.stationState[loc]) { opState.stationState[loc].hasPart = false; return; }
  const b = opState.boxState[loc];
  if (b.type === "in")   b.remaining = Math.max(0, b.remaining - 1);
  if (b.type === "swip") b.has_part = false;
}

function doDrop(loc, opState) {
  if (opState.stationState[loc]) { opState.stationState[loc].hasPart = true; return; }
  const b = opState.boxState[loc];
  if (b.type === "out")  b.count += 1;
  if (b.type === "swip") b.has_part = true;
}

function updateOperators(opState, opNames, scenario, simClock, taktTime, taktResetCount, speed) {
  const absTime    = taktResetCount * taktTime + simClock;
  const locCenters  = opState._locCenters;

  opNames.forEach(op => {
    if (opState.isBlocked[op]) return; // frozen — nothing to update

    const seq = opState.sequence[op];
    if (!seq || seq.length === 0) return;

    let safety = 0;
    while (safety++ < 20) {
      const step   = seq[opState.seqIdx[op]];
      const target = locCenters[step.loc];
      const pos    = opState.opPositions[op];

      if (opState.phase[op] === "walking") {
        if (!target) {
          opState.phase[op] = step.action === "work" ? "working" : "instant";
          continue;
        }
        const dx = target.x - pos.x, dy = target.y - pos.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist <= speed || dist === 0) {
          pos.x = target.x;
          pos.y = target.y;
          opState.phase[op] = step.action === "work" ? "working" : "instant";
          continue;
        } else {
          pos.x += (dx / dist) * speed;
          pos.y += (dy / dist) * speed;
          break; 
        // still walking this frame — carried part follows via pos below
        }
      }

      if (opState.phase[op] === "instant") {
        if (step.action === "pick") {
          if (!canPick(step.loc, opState, scenario)) {
            opState.isBlocked[op]     = true;
            opState.blockedReason[op] = `'${step.loc}' has no part available to pick.`;
            break;
          }
          doPick(step.loc, opState);
          opState.carrying[op] = true;
        } else if (step.action === "drop") {
          if (!canDrop(step.loc, opState, scenario)) {
            opState.isBlocked[op]     = true;
            opState.blockedReason[op] = `'${step.loc}' is at capacity — cannot drop part.`;
            break;
          }
          doDrop(step.loc, opState);
          opState.carrying[op] = false;
        }
        opState.seqIdx[op] = (opState.seqIdx[op] + 1) % seq.length;
        opState.phase[op]  = "walking";
        continue;
      }

      if (opState.phase[op] === "working") {
        const cycleTime = (scenario.stations[step.loc] || {}).cycle_time || 0;
        if (opState.workStartAbsTime[op] === null) {
          opState.workStartAbsTime[op] = absTime;
        }
        if (absTime - opState.workStartAbsTime[op] >= cycleTime) {
          opState.workStartAbsTime[op] = null;
          opState.seqIdx[op] = (opState.seqIdx[op] + 1) % seq.length;
          opState.phase[op]  = "walking";
          continue;
        }
        break; // still working this frame
      }

      break;
    }

    // Carried-part sprite offset in the direction of travel, so it reads
    // as "being carried forward" rather than a fixed badge position.
    const pos = opState.opPositions[op];
    if (opState.carrying[op]) {
        const prev = opState._prevPos ? opState._prevPos[op] : null;
        let dx = 0, dy = -1; // default: offset upward if not yet moving
        if (prev) {
            const mx = pos.x - prev.x, my = pos.y - prev.y;
            const mag = Math.sqrt(mx * mx + my * my);
            if (mag > 0.01) { dx = mx / mag; dy = my / mag; }
        }
        opState.partPositions[op] = { x: pos.x + dx * 16, y: pos.y + dy * 16 };
    } else {
        opState.partPositions[op] = null;
    }

    // Track this frame's position for next frame's direction calc.
    if (!opState._prevPos) opState._prevPos = {};
    opState._prevPos[op] = { x: pos.x, y: pos.y };
  });

  // ---- resting parts at stations / swip boxes (visual only) ----
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
}