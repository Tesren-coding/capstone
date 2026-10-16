# Line Builder update — New Line and adjustable direction image

## New Line

The **+ New Line** button in the Line Builder toolbar clears the current **unsaved builder canvas** and starts a new draft with:

- **Raw Material** (IN box; default starting count 10)
- **Line Direction** (the PNG in `static/images/line_direction.png`)
- **Finished Goods** (OUT box; default capacity 50)

Stations, operators, sequences, selections, prior filename/revision and planning-review metadata are reset; takt time returns to 30 minutes, IDs are reset, the view returns to 100%, and the new draft is kept in the browser session. You can edit and save this as a new scenario. It does **not** delete or overwrite any existing SQL Server records or JSON exports. A confirmation appears if the current draft has unsaved changes; Cancel preserves your work.

## Resize, rotate, flip

Click **Line Direction** on the canvas to open its editor. You can:

- Drag it to reposition it.
- Drag the small bottom-right square to resize; this works at different zoom levels.
- Set precise width and height using the panel inputs.
- Enter a rotation in degrees, or click the two 90-degree rotation buttons.
- Flip the image horizontally or vertically, independently.

The text label stays upright. Movement, dimensions, angle and flips are persisted as ordinary fields in the scenario JSON payload (`x`, `y`, `w`, `h`, `rotation`, `flip_horizontal`, `flip_vertical`). Existing direction images without transform fields still display as unrotated, unflipped; old saved scenarios are not edited merely by opening them. The direction item is decorative, and cannot be a material pick/drop location.

## SQL storage

No database migration or table modifications are needed. The existing `dbo.CapstoneSaves` JSON payload supports the optional marker transform fields. Continue launching this project in your configured SQL Server storage mode; do not overwrite your existing database. Other builder functionality, C-layout generation and operator-tracer playback are retained.

## Regression tests

- `node tests/test_builder_snapping.mjs`
- `node tests/test_line_direction.mjs`
- `python -m unittest discover -s tests -p test_line_direction_schema.py -v`
- `python tests/browser_builder_smoke.py`
- `python tests/browser_new_line_direction.py`

The browser tests use a mocked API and verify UI interactions and serialized data. They do not require a live SQL Server. The complete Flask/SimPy suite requires the dependencies in `requirements.txt` and a suitable runtime.

## Default blank-line layout (reference update)

For a freshly created line (including **+ New Line**), the direction marker now defaults to **875 × 85 canvas units** at **(170, 190)**. Raw Material starts at **(1070, 155)** and Finished Goods at **(1070, 250)**, vertically stacked to the arrow's right, matching the supplied reference composition.

User-resized, rotated, flipped and previously saved direction markers keep their own stored dimensions and coordinates on load. A new line resets to this default. When generated from Builder Setup, the same marker size is used but positioned above the C-shaped stations; existing generated Incoming/Outgoing geometry is preserved.

Regression checked with `python tests/browser_new_line_direction.py` and `python tests/browser_builder_smoke.py` plus `node tests/test_builder_snapping.mjs` and the standalone direction/schema geometry tests. This visual-only default change requires **no SQL migration**.
