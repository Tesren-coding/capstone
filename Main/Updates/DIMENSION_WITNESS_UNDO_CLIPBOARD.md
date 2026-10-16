# Dimension witness lines and canvas shortcuts

## Dimension tool

1. Click **↔ Dimension**, then click two boundary points on a station or material box. The endpoints snap anywhere along their edges (or to corners). Click a second point to save the measurement.
2. The blue dimension line begins 35 canvas units above/to the side of the measured segment; dotted extension/witness lines connect it to the original object edges.
3. Drag the **blue dimension line or its label** to change the perpendicular offset. The measurement anchors stay attached. The extension lines update as stations move and resize.
4. Click a selected ruler's endpoint circle to adjust the measured point. Press Escape to leave measurement mode.
5. Measurements use the configured **Scale (px/m)** and display meters to two decimals. New `offset` is optional in schema v2 and old ruler saves default to offset 0.

## Keyboard shortcuts (only when not editing a text field)

- **Ctrl+Z** / **Cmd+Z**: undo the last layout edit; up to 80 checkpoints per line.
- **Ctrl+Y** or **Ctrl+Shift+Z** / **Cmd+Shift+Z**: redo (until another edit is made).
- **Ctrl+C** / **Cmd+C**: copy selected canvas objects into the Line Builder's internal clipboard.
- **Ctrl+V** / **Cmd+V**: paste duplicates, offset by 35 units each time.

Ctrl-click or use marquee selection to copy a group. Duplicate stations and operators get unique IDs; included operator attachments and dimension anchors are mapped to new stations. Pasting an object without its referenced station detaches its home/measurement anchor while retaining its visible position.

Clipboard is internal to the open browser page; it does not copy JSON to the operating-system clipboard. Ctrl+C/V/Z inside normal text inputs use their native browser behavior. Undo history resets when creating/loading a different line; undo does not reverse changes to a previously saved SQL record.

## Changed files

- `static/js/dimension-tools.js`: true edge snapping, offset line geometry, dotted witness lines.
- `static/js/builder.js`: offset-line hit-testing and dragging, keyboard undo/redo/copy/paste, ID/anchor remapping.
- `scenario_schema.py`: optional validated numeric dimension offset.
- `templates/builder.html`: help/tooltip text.
- `tests/browser_dimension_shortcuts.py`, `tests/test_dimension_schema.py`: regression coverage.
