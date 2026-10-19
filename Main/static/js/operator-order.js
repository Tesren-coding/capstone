// Operator IDs are also their displayed names. Reordering changes the ID slots,
// not the underlying operator's color, position, attachments or work sequence.
const idCollator = new Intl.Collator('en', {numeric: true, sensitivity: 'base'});

export function orderedOperatorIds(operators) {
    return Object.keys(operators).sort((a, b) => idCollator.compare(a, b) || a.localeCompare(b));
}

export function remapOperatorOrder(operators, orderedIds) {
    const existing = orderedOperatorIds(operators);
    if (orderedIds.length !== existing.length ||
        new Set(orderedIds).size !== existing.length ||
        orderedIds.some(id => !Object.hasOwn(operators, id))) {
        throw new Error('Operator reordering requires every existing operator exactly once.');
    }
    const mapping = {};
    const reordered = {};
    orderedIds.forEach((oldId, index) => {
        const newId = `Op${index + 1}`;
        mapping[oldId] = newId;
        reordered[newId] = {...operators[oldId], name: newId};
    });
    return {
        operators: reordered,
        mapping,
        changed: orderedIds.some(oldId => oldId !== mapping[oldId] || operators[oldId].name !== mapping[oldId]),
    };
}
