# Operator ID drag-to-reorder (2026-10-19)

## Using the control

In **Line Builder**, click **↕ Reorder Operators** next to **+ Operator**.
Drag the ⠿ handle on an operator row above or below another operator.
For keyboard access, focus its handle and press **Alt + Up/Down**.

The **list position becomes the operator ID**: top is `Op1`, next is `Op2`, etc.
Names always equal their IDs. The actual operator object retains its color,
coordinates, attached station, standing-side sequences and assigned processes.
The right-side editor follows the selected physical operator if their ID changes.

The older **Renumber Operators** button remains available to close gaps without
changing the numerical order.

## Changes

- `templates/builder.html`: new reorder toggle and list.
- `static/js/operator-order.js`: pure ID sort and identity remapping.
- `static/js/builder.js`: render list, mouse/keyboard reordering, selection remapping,
  undo support, draft saving, and shared renumber utility.
- `tests/browser_reorder_operators.py`: browser workflow verification.
- `tests/test_operator_order.mjs`: pure reorder mapping cases.

## Data compatibility

There is no database/schema migration: saved operator objects are still keyed by
`Op<number>`, with `name` matching the key. Historical scenarios are left unchanged
unless the user chooses to reorder or renumber them. The simulation hover legend
already sorts operator IDs numerically, so it reflects the new order after running.

**Note:** Reordering operators renames operator ID slots, but does not reorder
their internal sequences of work steps. Those sequences are kept attached to the
operator being moved. Saved SQL scenarios update only when explicitly saved.
