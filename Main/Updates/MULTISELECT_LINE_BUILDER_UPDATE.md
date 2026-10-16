# Line Builder: marquee multi-selection and additional direction markers

## Canvas controls

- Drag from empty canvas to draw a blue selection rectangle (marquee). Any station, operator, material box, or line-direction marker intersecting the rectangle is selected.
- Hold Ctrl (Cmd on macOS) while clicking an item to add/remove it from the selection. Ctrl-drag from empty canvas adds to an existing selection.
- Drag any highlighted item to move the entire selected group without snapping the stations apart. Operators attached to moved stations follow them and remain attached. A selected operator moved independently of its station detaches.
- When several objects are selected, the side panel offers **Delete N Selected**. Press Escape or click empty canvas to clear the selection.
- Dotted operator placement circles appear only when placing, moving, or editing an operator, not when a station is clicked.
- **+ Line Direction** puts a new arrow on the canvas at the clicked point with default size 875 x 85. The arrow editor opens immediately; rotate, flip, drag and resize work as for the default arrow.

## Compatibility

The selection state is client-side only and is never saved to SQL or scenario JSON. The new direction marker uses the existing `type: direction` schema, so no database migration is necessary.

## Tests

From the project root, where Playwright and Chromium are available:

```
python tests/browser_multiselect.py
python tests/browser_builder_smoke.py
python tests/browser_new_line_direction.py
python tests/browser_rename_scenario.py
node tests/test_builder_snapping.mjs
node tests/test_line_direction.mjs
```

The full Flask/SimPy/SQL integration tests require their dependencies and a configured database.
