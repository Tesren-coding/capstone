# Operator legend: natural numeric order

## Problem

The simulation formerly set `opNames = Object.keys(scenario.operators)`. Because
operator IDs are ordinary string keys such as `Op1`, `Op2`, and `Op10`, their
iteration order follows JSON/object insertion order, **not** operator number.
Saving, loading, deleting, or copying operators may therefore produce a
surprising sequence in the legend. Simple alphabetical `.sort()` would also put
`Op10` before `Op2`.

## Change

`static/js/operator-highlight.js` now exports `sortOperatorIds(ids)` using
`Intl.Collator` with `numeric: true`. `static/js/playback.js` uses this once when
creating `opNames`, so the accessible hover chips, canvas legend, hover hit
targets, and playback drawing share a consistent order: `Op1, Op2, ..., Op10`.

Sorting is **presentation-only**: operator IDs, names, assignments, saved JSON,
events, walking calculations, and SQL storage remain unchanged. The function
returns a new array rather than mutating scenario objects.

## Testing

Run `node tests/test_operator_highlight.mjs` and
`python tests/browser_operator_highlight.py`. The browser fixture deliberately
stores `Op10`, then `Op2`, then `Op1` and asserts the rendered order is
`Op1`, `Op2`, `Op10`.
