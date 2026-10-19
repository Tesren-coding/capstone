# Export update — Part icons, route arrows and the imported SWCS workbook

## SWS / Standard Work Sheet (.pptx)

The exporter uses the builder layout and still includes all Line Direction arrows, preserving their positions, dimensions, rotations and flip settings. Material boxes (`in`, `out`, `swip`) have dotted outlines. All boxes of type `swip` are labelled exactly `SWIP`, rather than using their unique saved names.

The browser's `static/images/Part.png` appears at locations holding starting inventory: stations with `has_part`, SWIP boxes with `has_part`, and IN boxes with positive `start_count`. The label in the legend explains the part icon; the IN box continues to show its configured quantity. OUT boxes do not show initial-part icons.

Route segments use editable curved freeform PowerPoint lines and small destination arrowheads. Each work-sequence visit gets its own circular step number; repeated visits and shared destinations use offset badges and thin leader lines to identify the correct station. The full-line overview and individual operator slides are both included. Arrow curvature is intended for clarity, not aisle/path collision avoidance.

## SWCS / Standard Work Combination Sheet (.xlsx)

The actual user-supplied `HA Stage 4 Nozzle SWCS 031125 .xlsx` has been included unmodified as `resources/HA_Stage_4_Nozzle_SWCS_template.xlsx`, and the exporter creates a copy preserving its native Excel drawings, fixed labels, formatting and styles. **Only blue-formatted input cells are rewritten**: line/framesize metadata, operator ID, step number, operation description, manual time, automatic time, walking time, and provided total fields. Missing inputs are blank rather than fabricated. Walking time uses the same configured px/m scale and walking speed as the simulation.

The template has a finite number of blue step rows per page. Further steps get continuation sheets using the same imported template, so no planned sequence step is silently discarded. Lines for more than six operators also receive additional template sheets.

**Drawing accuracy limitation:** The imported line/squiggle/arrow shapes are *sample shapes* with coordinates from the original repair-line study, which do not necessarily match the new cycle, manual, automatic, or walking durations. They are preserved as editable Excel objects, but **the user must move, delete and re-draw them in Excel to match the newly populated times**. Automatically generating *accurate* SWCS lines in that particular template will require a separate timeline mapping tool, calibrated to the template's exact time-axis scale and the desired overlap conventions. Do not treat the retained sample drawings as verified time charts.

The SWS and SWCS are draft engineering planning exports, not approved shop-floor standard work. Quality, safety and other detailed work instructions must be verified independently.

## Files changed

- `standard_work_exports.py`: SWS part icons, dotted box borders, separate circular step labels, curved path direction arrows; SWCS delegates to original-template exporter.
- `swcs_preserved_template.py`: copies and edits only blue cells of the original workbook, retaining drawing objects and adding continuation operator sheets as required.
- `resources/HA_Stage_4_Nozzle_SWCS_template.xlsx`: original reference workbook.
- `templates/simulate.html`: clarifies the SWCS line-editing limitation.
- `tests/test_standard_work_exports.py`: verifies layout, part icons, arrow transforms and workbook preservation.

No SQL schema changes or new Python dependencies.
