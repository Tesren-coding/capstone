// Presentation-only helpers for highlighting each operator's full work area.
// Never change saved scenarios or simulation event contents to calculate focus.
// Scenario operators are stored by ID in an object. Its insertion order is NOT
// a reliable operator-number order (for example Op10 can precede Op2).
const operatorIdCollator = new Intl.Collator('en', {numeric: true, sensitivity: 'base'});
export function sortOperatorIds(ids) {
    return [...ids].sort((a, b) => operatorIdCollator.compare(a, b) || a.localeCompare(b));
}
export function visitedLocationsForOperator(operator, scenario) {
    const visited = new Set();
    const locations = {...(scenario.stations || {}), ...(scenario.boxes || {})};
    const home = operator?.attached_to?.station_id;
    if (home != null && scenario.stations?.[String(home)]) visited.add(String(home));
    for (const step of operator?.sequence || []) {
        const loc = String(step.loc ?? '');
        if (locations[loc] && locations[loc].type !== 'direction') visited.add(loc);
    }
    return visited;
}

// The canvas legend stays at a fixed pixel location, independent of zoom/pan.
// Share its hitboxes with the renderer so hover and drawing cannot drift apart.
export function operatorLegendEntries(names, canvasHeight) {
    let x = 20;
    return names.map(id => {
        const width = Math.max(94, 32 + String(id).length * 8);
        const entry = {id, x, y: canvasHeight - 30, width,
            left: x - 12, right: x + width - 12,
            top: canvasHeight - 53, bottom: canvasHeight - 9};
        x += width;
        return entry;
    });
}

export function operatorAtLegendPoint(point, names, canvasHeight) {
    return operatorLegendEntries(names, canvasHeight).find(entry =>
        point.x >= entry.left && point.x <= entry.right &&
        point.y >= entry.top && point.y <= entry.bottom)?.id || null;
}
