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
    phase: {},                 // "walking" | "instant" | "working" | "idle"
    carrying: {},
    workStartAbsTime: {},
    cycleStartAbsTime: {},     // when this operator's current takt cycle began
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

    opState.sequence[op]          = seq;
    opState.seqIdx[op]            = 0;
    opState.phase[op]             = "walking";
    opState.carrying[op]          = false;
    opState.workStartAbsTime[op]  = null;
    opState.cycleStartAbsTime[op] = 0;
    opState.isBlocked[op]         = false;
    opState.blockedReason[op]     = null;

    const home = seq.length > 0 && locCenters[seq[0].loc] ? locCenters[seq[0].loc] : { x: 0, y: 0 };
    opState.opPositions[op]   = { x: home.x, y: home.y };
    opState.partPositions[op] = null;
  });

  return opState;
}

function canPick(loc, opState) {
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

function updateOperators(opState, opNames, scenario, simClock, taktTime, taktResetCount, speed, deltaMs, msPerSimMinute) {
  const absTime      = taktResetCount * taktTime + simClock;
  const locCenters    = opState._locCenters;
  const deltaSimTime  = deltaMs / msPerSimMinute;  // same time scale as simClock/absTime
  const stepDist      = speed * deltaSimTime;       // pixels to move THIS frame, in simulated time

  opNames.forEach(op => {
    const seq = opState.sequence[op];
    if (!seq || seq.length === 0) return;

    // ---- Blocked: keep re-checking the exact step that failed ----
    if (opState.isBlocked[op]) {
      const step = seq[opState.seqIdx[op]];
      const stillBlocked =
        (step.action === "pick" && !canPick(step.loc, opState)) ||
        (step.action === "drop" && !canDrop(step.loc, opState, scenario));

      if (stillBlocked) {
        const pos = opState.opPositions[op];
        opState.partPositions[op] = opState.carrying[op] ? { x: pos.x, y: pos.y } : null;
        return;
      }

      // Condition cleared (e.g. another operator just dropped a part
      // this operator was waiting on) — unblock and retry this step.
      opState.isBlocked[op]     = false;
      opState.blockedReason[op] = null;
      opState.phase[op]         = "instant";
      // fall through into the normal state machine below
    }

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
        if (dist <= stepDist || dist === 0) {
          pos.x = target.x;
          pos.y = target.y;
          opState.phase[op] = step.action === "work" ? "working" : "instant";
          continue;
        } else {
          pos.x += (dx / dist) * stepDist;
          pos.y += (dy / dist) * stepDist;
          break; // still walking this frame
        }
      }

      if (opState.phase[op] === "instant") {
        if (step.action === "pick") {
          if (!canPick(step.loc, opState)) {
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

        const isLastStep = opState.seqIdx[op] === seq.length - 1;
        opState.seqIdx[op] = (opState.seqIdx[op] + 1) % seq.length;

        opState.phase[op] = isLastStep ? "idle" : "walking";
        continue;
      }

      if (opState.phase[op] === "working") {
        const cycleTime = (scenario.stations[step.loc] || {}).cycle_time || 0;
        if (opState.workStartAbsTime[op] === null) {
          opState.workStartAbsTime[op] = absTime;
        }
        if (absTime - opState.workStartAbsTime[op] >= cycleTime) {
          opState.workStartAbsTime[op] = null;

          const isLastStep = opState.seqIdx[op] === seq.length - 1;
          opState.seqIdx[op] = (opState.seqIdx[op] + 1) % seq.length;

          opState.phase[op] = isLastStep ? "idle" : "walking";
          continue;
        }
        break; // still working this frame
      }

      if (opState.phase[op] === "idle") {
        const nextBoundary = opState.cycleStartAbsTime[op] + taktTime;
        if (absTime >= nextBoundary) {
          opState.cycleStartAbsTime[op] = nextBoundary;
          opState.phase[op] = "walking";
          continue;
        }
        break; // still idling this frame
      }

      break;
    }

    const finalPos = opState.opPositions[op];
    const PART_CARRY_OFFSET_X = 14;
    const PART_CARRY_OFFSET_Y = -14;
    opState.partPositions[op] = opState.carrying[op]
      ? { x: finalPos.x + PART_CARRY_OFFSET_X, y: finalPos.y + PART_CARRY_OFFSET_Y }
      : null;
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