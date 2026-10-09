// static/js/state.js
//
// Visual choreography engine for simulate.html.
//
// Operators walk their own sequence (pick/work/drop), self-paced.
// If a pick/drop/work precondition fails, that operator becomes
// blocked AND the entire simulation halts (opState.stopReason is set)
// — this is a hard stop, not a per-operator freeze. The caller
// (simulate.html) is responsible for checking opState.stopReason each
// frame and setting isRunning = false + displaying the message.
//
// Andon: opState.stationAndon[sid] is "green" or "red". A station is
// red only if it is the specific location referenced by the current
// stopReason (i.e., it's the cause of the stoppage).

function buildOperatorState(simEvents, stationCenters, boxCenters, opNames, scenario) {
  const locCenters = Object.assign({}, stationCenters, boxCenters);

  const opState = {
    _locCenters: locCenters,
    sequence: {},
    seqIdx: {},
    phase: {},                 // "walking" | "instant" | "working" | "returning" | "idle"
    carrying: {},
    workStartAbsTime: {},
    cycleStartAbsTime: {},
    opPositions: {},
    partPositions: {},
    isBlocked: {},
    blockedReason: {},
    blockedLoc: {},
    droppedParts: {},
    stationState: {},
    boxState: {},
    stationAndon: {},
    stopReason: null,          // set once, non-null once the sim halts
  };

  for (const sid in scenario.stations) {
    opState.stationState[sid] = { hasPart: !!scenario.stations[sid].has_part };
    opState.stationAndon[sid] = "green";
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
    opState.blockedLoc[op]        = null;

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

function canWork(loc, opState) {
  // Only stations can be "worked" on. If it's genuinely a station,
  // require a part to be present. Anything else (shouldn't normally
  // happen) is permitted to avoid a false block on malformed data.
  if (opState.stationState[loc]) return opState.stationState[loc].hasPart;
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

function triggerStop(opState, op, loc, reasonText) {
  opState.isBlocked[op]     = true;
  opState.blockedReason[op] = reasonText;
  opState.blockedLoc[op]    = loc;
  if (!opState.stopReason) {
    opState.stopReason = reasonText; // first cause wins — the whole sim halts on this
  }
}

function updateOperators(opState, opNames, scenario, simClock, taktTime, taktResetCount, speed, deltaMs, msPerSimMinute) {
  const absTime      = taktResetCount * taktTime + simClock;
  const locCenters    = opState._locCenters;
  const deltaSimTime  = deltaMs / msPerSimMinute;
  const stepDist      = speed * deltaSimTime;

  opNames.forEach(op => {
    if (opState.isBlocked[op]) return; // hard stop — no re-checking, stays frozen permanently

    const seq = opState.sequence[op];
    if (!seq || seq.length === 0) return;

    let safety = 0;
    while (safety++ < 20) {
      const pos = opState.opPositions[op];

      // ---- Returning to home position after finishing the sequence ----
      if (opState.phase[op] === "returning") {
        const homeLoc = seq[0].loc;
        const target  = locCenters[homeLoc];
        if (!target) { opState.phase[op] = "idle"; continue; }

        const dx = target.x - pos.x, dy = target.y - pos.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist <= stepDist || dist === 0) {
          pos.x = target.x;
          pos.y = target.y;
          opState.phase[op] = "idle";
          continue;
        } else {
          pos.x += (dx / dist) * stepDist;
          pos.y += (dy / dist) * stepDist;
          break;
        }
      }

      const step   = seq[opState.seqIdx[op]];
      const target = locCenters[step.loc];

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

          if (step.action === "work") {
            if (!canWork(step.loc, opState)) {
              const stName = (scenario.stations[step.loc] || {}).name || step.loc;
              triggerStop(opState, op, step.loc,
                `${op} has no part to work on at station '${stName}'.`);
              break;
            }
            opState.phase[op] = "working";
          } else {
            opState.phase[op] = "instant";
          }
          continue;
        } else {
          pos.x += (dx / dist) * stepDist;
          pos.y += (dy / dist) * stepDist;
          break;
        }
      }

      if (opState.phase[op] === "instant") {
        if (step.action === "pick") {
          if (!canPick(step.loc, opState)) {
            triggerStop(opState, op, step.loc,
              `${op} has no part available to pick at '${step.loc}'.`);
            break;
          }
          doPick(step.loc, opState);
          opState.carrying[op] = true;
        } else if (step.action === "drop") {
          if (!canDrop(step.loc, opState, scenario)) {
            triggerStop(opState, op, step.loc,
              `${op} cannot drop — '${step.loc}' is at capacity.`);
            break;
          }
          doDrop(step.loc, opState);
          opState.carrying[op] = false;
        }

        const isLastStep = opState.seqIdx[op] === seq.length - 1;
        opState.seqIdx[op] = (opState.seqIdx[op] + 1) % seq.length;
        opState.phase[op]  = isLastStep ? "returning" : "walking";
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
          opState.phase[op]  = isLastStep ? "returning" : "walking";
          continue;
        }
        break;
      }

      if (opState.phase[op] === "idle") {
        const nextBoundary = opState.cycleStartAbsTime[op] + taktTime;
        if (absTime >= nextBoundary) {
          opState.cycleStartAbsTime[op] = nextBoundary;
          opState.phase[op] = "walking";
          continue;
        }
        break;
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

  // ---- andon: red only for the station causing the current stoppage ----
  for (const sid in opState.stationAndon) {
    opState.stationAndon[sid] = "green";
  }
  if (opState.stopReason) {
    opNames.forEach(op => {
      if (opState.isBlocked[op] && opState.blockedLoc[op] && opState.stationAndon[opState.blockedLoc[op]] !== undefined) {
        opState.stationAndon[opState.blockedLoc[op]] = "red";
      }
    });
  }
}