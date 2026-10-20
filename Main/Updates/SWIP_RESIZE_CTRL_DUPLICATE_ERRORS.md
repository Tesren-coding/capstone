# Line Builder: SWIP resize, double-click naming, Ctrl-drag duplication

## Changes

- Select a SWIP box, then drag any of its four corner handles to resize. The opposite corner remains fixed. Its editor also provides width/height in metres using the same px/m scale as stations.
- A SWIP box has minimum canvas size 44 x 38 px for legible controls. The on-screen box dimensions describe layout, **not** how many pieces it can hold: a SWIP box remains single-part.
- Double-click a station, IN/OUT box or SWIP box to select the item and focus/select its **Name** field in the item editor.
- Operator names are their `Op1`, `Op2`, etc. IDs and cannot be renamed from a separate field. Use Reorder Operators to change numbering.
- Ctrl-click adds/removes an item from the current selection. **Ctrl-drag** an item to duplicate it; if it belongs to a multi-selection, the entire selection is duplicated and follows the pointer. Cloned stations, boxes, operators and dimensions get new IDs; copied references to other selected objects are remapped. Undo restores the state before copying. Ctrl+C/V remain supported.
- Scale changes refresh the displayed SWIP width and height fields.

## Wait until station processing is complete

`wait_for_process` is a flag on a `pick` action. The simulator always waits if a station is busy or empty. When this box is checked, it additionally waits until all processes assigned to that station by **any** operator have completed before allowing a pickup. Default higher-level Transfer/Full Cycle tasks set this flag to true; users can override it for intentional intermediate pickup. If unchecked, pickups can occur while required processes remain unfinished (when the station is otherwise not busy).

## Existing validation/error logic (unchanged)

**Input validation** (`scenario_schema.py`): number/range/type requirements; positive takt, layout scale and walking speed; valid station/box geometry; station process IDs/names/manual+auto time; legal process/station/box references, action types and station-side assignments; valid operator colors/attachments and unique station-side attachments; carrying consistency (no double pick, no drop without pickup, no work while carrying, no leftover carried part at cycle end); and planning-origin material-flow review when required.

**Runtime** (`simulation.py`): waits for an occupied/busy station to clear, station stock, required processing completion (if checked), an available SWIP part, and station space. Hard `blocked` events stop on double pickup, pickup without stock (notably an exhausted IN box), drop without a carried part, or drop into a full material box. Playback renders hard-block reasons in red.

**Not yet covered**: general deadlock/circular-wait detection, reliable starvation timeout, detailed part routing/quality conformance, and proof that every expected part/process flow is completed. A run stalled on unresolved waits can reach its 100-takt time horizon and be labeled complete even without useful throughput. Improve this before using results to approve production line designs.
