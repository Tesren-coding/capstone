// Starting SWIP summary for the simulation dashboard.
// SWIP is defined here as the configured starting parts that seed the line:
// - parts starting in stations
// - occupied SWIP boxes
// - starting parts in IN boxes (raw input reservoirs)
// Decorative arrows and OUT boxes are excluded.
export function startingSwipMetrics(scenario) {
    const stations = Object.values(scenario?.stations || {});
    const boxes = Object.values(scenario?.boxes || {});
    const swipBoxes = boxes.filter(box => box?.type === 'swip');
    const inBoxes = boxes.filter(box => box?.type === 'in');

    const stationParts = stations.filter(station => station?.has_part === true).length;
    const swipBoxesWithParts = swipBoxes.filter(box => box?.has_part === true).length;
    const inBoxParts = inBoxes.reduce((sum, box) => sum + Math.max(0, Number(box?.start_count) || 0), 0);

    const totalSwip = stationParts + swipBoxesWithParts + inBoxParts;
    return {
        totalSwip,
        stationParts,
        swipBoxesWithParts,
        inBoxParts,
        swipBoxes: swipBoxes.length,
        inBoxes: inBoxes.length,
        categories: [
            { key: 'stations', label: 'Stations with parts', value: stationParts, color: '#2b65ad' },
            { key: 'swipBoxes', label: 'SWIP boxes with parts', value: swipBoxesWithParts, color: '#e28b18' },
            { key: 'inBoxes', label: 'IN boxes starting parts', value: inBoxParts, color: '#2f9d57' },
        ],
    };
}

// Kept as a reusable calculation for future playback analytics; the current
// dashboard intentionally shows only the starting SWIP pie chart.
export function liveLineMetrics(state) {
    if (!state) return {currentWip: 0, stationParts: 0, swipBoxParts: 0, partsCarried: 0, finishedGoods: 0, rawRemaining: 0};
    const stations = Object.values(state.stationState || {});
    const boxes = Object.values(state.boxState || {});
    const stationParts = stations.filter(station => station.hasPart === true).length;
    const swipBoxParts = boxes.filter(box => box.type === 'swip' && box.has_part === true).length;
    const partsCarried = Object.values(state.carrying || {}).filter(Boolean).length;
    const finishedGoods = boxes.reduce((sum, box) => sum + (box.type === 'out' ? Math.max(0, Number(box.count) || 0) : 0), 0);
    const rawRemaining = boxes.reduce((sum, box) => sum + (box.type === 'in' ? Math.max(0, Number(box.remaining) || 0) : 0), 0);
    return {
        currentWip: stationParts + swipBoxParts + partsCarried,
        stationParts,
        swipBoxParts,
        partsCarried,
        finishedGoods,
        rawRemaining,
    };
}
