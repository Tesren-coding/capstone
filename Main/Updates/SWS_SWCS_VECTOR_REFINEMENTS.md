# Standard work exports — operator-step badges and graphical SWCS timeline

## SWS (.pptx)

- Overlapping/repeated stop numbers for one operator at nearly the same physical point are combined as a comma-separated series, e.g. `1, 3, 5`.
- Number labels are offset from their true standing points using collision-avoidance placement; a short colored leader connects each badge back to the actual location.
- On the overview slide, each annotation includes its operator ID. Individual operator slides use step numbers only.
- Line Direction markers (including multiple directions) remain present behind stations and operator curves. The exported PNG retains position, size, angle and horizontal/vertical mirroring.
- All shapes, labels and graphics can be edited in PowerPoint.

## SWCS (.xlsx)

- Colored timing cells are replaced by a more traditional graphical combination timeline with editable native Excel DrawingML strokes.
- Manual work: orange solid line with forward arrow.
- Walking: purple zigzag (squiggly) path made of individually editable line segments, with an arrow.
- Automatic machine time: teal dashed line with arrow on the row below, allowing automatic dwell to overlap subsequent operator tasks.
- Each segment spans its scheduled timeline, with numeric times remaining available in the table. Very short steps may be only a few pixels wide at the selected print scale.
- Each operator still has a separate Excel worksheet, with editable rows and timing figures.
- Segments are first-pass planned timings; actual waiting, conflicts and certification are not inferred.

## Technical

- Exports continue to use the same Flask routes: `/export-sws` and `/export-swcs`.
- Native Excel drawing shapes are inserted with standard OOXML into the XLSX file after spreadsheet cells are written. Short walking strokes are visually enlarged to a minimum of 12px so their zigzag symbol is still recognizable; numeric times stay exact.
- No changes to the scenario/SQL Server schemas or operator sequences are required.
