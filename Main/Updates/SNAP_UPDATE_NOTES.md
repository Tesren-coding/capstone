# Station sizing and snapping update — 13 October 2026

## Changes

- Unified the C-shaped generator and C-shaped planning preview to 150×96 new-station dimensions, matching hand-created Line Builder stations. Manual and generated station size constants are shared by JavaScript; the Python generator uses the same 150×96 contract.
- Added a snapping station insertion ghost and responsive alignment when dragging stations. Stations can align on edges/centers or sit adjacent with a 22-unit gap. Snapping respects the current canvas zoom; free dragging is unchanged away from targets.
- Added four operator side anchors and dotted placement guides. Each anchor has a 10-unit visible clearance from the station edge and uses the existing operator radius of 16 units.
- Operators can attach to a vacant anchor, follow their station on drag, detach on dragging away, and reattach to another anchor.
- Added `attached_to` metadata (optional for scenario v2) with station ID and side. IDs remap on renumbering/swapping/reordering; removing a station clears the metadata but retains operator coordinates.
- Old scenario files without an attachment remain free-floating and are not resized or re-aligned. New attachments are validated during save/import/export.

## Verified here

- JavaScript geometry, insertion, zoom and remapping checks: **passed** (`node tests/test_builder_snapping.mjs`).
- Python standalone C-shaped layout and dimensions: **2 tests passed**.
- Scenario optional attachment validation and older dimensions: **3 tests passed**.
- Headless Chromium test using the real builder JavaScript with a mocked API: **passed**. It covers station insert/drag at 100% and 125%, operator anchor placement/detach/reattach, station ID renumber/reorder, scenario JSON save/load round trip, and detachment on station deletion.
- JavaScript syntax and Python compile checks: **passed**.

## Test environment restriction

This sandbox has no Flask or SimPy installed and cannot fetch Python dependencies from the network. Consequently, the existing complete Python test suite (previously reported as 56 passing tests) **could not be rerun here**. Install `requirements.txt`, then run `python -m unittest discover -s tests -v` in your normal environment. The browser test uses a mock API, so it does not replace a full running Flask integration test.
