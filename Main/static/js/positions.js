// static/js/positions.js
//
// Derives all canvas positions directly from the scenario's saved
// x/y/w/h values (set in builder.html). Stations and boxes store
// x,y as their TOP-LEFT corner; operators store x,y as their CENTER
// point directly (they have no w/h). centerOf() handles both cases
// correctly since missing w/h defaults to 0.

export function centerOf(rect) {
  return {
    x: rect.x + (rect.w || 0) / 2,
    y: rect.y + (rect.h || 0) / 2,
  };
}

export function buildPositionsFromScenario(scenario) {
  const stationPositions = {};
  const stationCenters   = {};
  for (const sid in scenario.stations || {}) {
    const s = scenario.stations[sid];
    const rect = { x: s.x, y: s.y, w: s.w || 0, h: s.h || 0 };
    stationPositions[sid] = rect;
    stationCenters[sid]   = centerOf(rect);
  }

  const boxPositions = {};
  const boxCenters   = {};
  for (const bid in scenario.boxes || {}) {
    const b = scenario.boxes[bid];
    const rect = { x: b.x, y: b.y, w: b.w || 0, h: b.h || 0 };
    boxPositions[bid] = rect;
    boxCenters[bid]   = centerOf(rect);
  }

  return {
    stationPositions,
    boxPositions,
    stationCenters,
    boxCenters,
  };
}

