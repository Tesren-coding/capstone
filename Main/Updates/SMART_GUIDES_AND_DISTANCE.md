# Smart snapping, alignment guides, and physical distances

This iteration adds canvas alignment and measurement to the Line Builder. It does **not** add station corner resizing, operator-legend filtering, utilization/SWIP dashboards, or worksheet export; those features remain separate follow-ups.

## Use

- Keep **Snap + measure** checked in the canvas controls. Drag a station, SWIP/IN/OUT box, or Line Direction image close to another object's **left/right/top/bottom edge or center**. A pink alignment line appears while dragging. The label reads `Edge`, `Center`, or `Gap`.
- Stations can still dock side-by-side with the existing **22 canvas-unit gap**; this is separate from exact edge alignment. Selected **groups** can align as a group without losing their relative spacing.
- Blue dimension lines indicate the *true, positive edge-to-edge gap* to the nearest object that overlaps along the perpendicular direction. They display **meters to two decimal places**, not screen pixels.
- Change **Scale (px/m)** in the toolbar to calibrate real dimensions. The default of 50 canvas units per meter is an editable starting estimate, **not a verified real-world scale**. Example: `22 / 50 = 0.44 m`. The same scale drives physical walking time in SimPy.
- Hold **Alt** during dragging to temporarily skip auto-snapping. Uncheck **Snap + measure** to disable both guides and auto-snapping. This preference is UI-only, not saved into scenario JSON.
- Snapping tolerance is a fixed screen-space distance, so changing browser canvas zoom does not alter how close the mouse must get before snapping.
- Operator icons retain their **station-side attachment snapping**; free operators may be dragged without interference from the rectangular alignment anchors. The new dimension guides do not change station standing-point assignments or routing to IN/OUT/SWIP centers.
- Guides disappear when dragging ends. The guide state is never serialized or sent to SQL Server.

## Files

`static/js/smart-guides.js`: pure snapping, measurement, and canvas guide rendering. `static/js/builder.js`: drag integration; `templates/builder.html`: toggle and instructions. Test with `node tests/test_smart_guides.mjs` and `python tests/browser_smart_guides.py` (Playwright and Chromium required for the latter).
