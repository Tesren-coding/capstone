# Line Builder: station resize and dimensioning tool

## Station sizing

1. Click a station to select it. Four small square handles appear at its corners.
2. Drag any corner. The **opposite corner stays fixed**, so the station does not expand from its center.
3. Pink alignment guides and blue gap measurements are available while resizing. Hold **Alt** to ignore alignment snapping.
4. Selected stations display their **width and height in meters**. You may also enter exact values in the station editor under **Width (m)** and **Height (m)**.
5. Attached operators follow their configured station sides automatically. Operator sequence standing points use the updated geometry. A station's process times and IDs are not changed by resizing.
6. Each station can have its own size. Default newly placed stations remain 150 × 96 canvas units. The minimum sizes for resizing are 64 × 55 canvas units, preserving readable text.

## Dimensioning

1. Click **↔ Dimension** in the top toolbar.
2. Click the first endpoint, then the second endpoint on the canvas. The green preview becomes a **saved blue ruler** with the distance shown to **two decimal places**.
3. Endpoints near a station or box corner, edge midpoint, or center **snap and attach** automatically, and follow that object during movement/resizing.
4. Click the ruler line to select it, then drag either round endpoint to edit the measurement. Drag the entire line to reposition it (this detaches the ruler from both attached objects).
5. Select a ruler and click **Delete** to remove just that measurement.
6. Click the Dimension button again or press **Escape** to cancel before placing the second endpoint.

Measurements use the same **Scale (px/m)** as physical walking-time calculations. A dimension is an annotation only and is **not** a physical obstacle or work sequence. Annotations are saved in the scenario's optional top-level `dimensions` object. Older scenarios without this property still load unchanged. There are no SQL table changes because SQL Server stores the scenario JSON document.

When an object with attached measurement endpoints is renumbered or reordered, the references follow it. Deleting an attached station or box leaves the dimension at its most recent physical coordinates.

## Files changed

- `static/js/builder.js` — mouse interaction, dimension state, station editor and serialization.
- `static/js/dimension-tools.js` — standalone geometric helpers and canvas drawing.
- `templates/builder.html` — Dimension button and helper text.
- `scenario_schema.py` — optional annotation validation.
- `tests/browser_builder_smoke.py` — inline browser test bundle recognizes new helper module.
- `tests/browser_station_dimensions.py`, `tests/test_station_dimension_geometry.mjs`, `tests/test_dimension_schema.py` — regression checks.

No changes to the SQL Server Express persistence layout or simulation engine.
