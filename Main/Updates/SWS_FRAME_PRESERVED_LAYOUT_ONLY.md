# SWS export: preserve the original frame

The PowerPoint SWS exporter uses the original uploaded `resources/SWS_Frame.pptx` as its source frame on the overview slide and every operator slide.

- Every original header/footer/table cell, symbol, and pre-existing legend remains unchanged and editable for the user.
- No automatic line name, part number, date, takt time, SWIP count, department, operator count, note, or legend text is inserted into the frame.
- Only the current line layout, dotted material-location boxes, starting-part icons, Line Direction image, and operator movement routes (curved arrows with numbered circular destination markers) are drawn over the blank central region.
- One movement number is shown per physical stop; consecutive Pick/Work/Drop operations at the same position do not create extra visit numbers.
- Operator-specific slides are copies of the unmodified frame rather than a duplicate of an already annotated overview.
- The drawing region is inset from the original frame's title/header, legend, and footer boundaries, with collision-aware offsets for numbered markers.

The exported SWS remains editable in PowerPoint. Detailed safety, quality and template metadata should be completed manually.
