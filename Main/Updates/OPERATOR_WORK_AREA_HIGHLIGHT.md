# Operator work-area highlighting

In **Simulation**, hover an operator in the legend at the bottom of the canvas or the accessible operator chips above the canvas. Stations and IN/OUT/SWIP boxes in the operator's **full saved sequence** remain solid; unrelated locations, their parts, other operators and tracers fade to 18% opacity. The operator's attached home station is also retained. The visual highlight does **not** depend on where the operator is at the current simulation time.

Click an operator chip to pin the focus; click it again or **Show all** to clear. Keyboard focus on a chip provides the same highlight. The canvas legend also responds to pointer hover even when zooming and panning the layout because its position is fixed in canvas screen pixels.

This is display-only: no changes to event scheduling, utilization, SQL records, schema versions or movement distances. The legend only appears when a scenario has been simulated.

## Blank line centering

The default blank layout now computes its center from the 2400 × 1042 drawing canvas, the 875 × 85 arrow and the two 90 × 60 material boxes. It retains the previous arrow/box relative offsets (25 horizontal gap, 35 arrow vertical offset and 95 vertical box offset) and no longer depends on hard-coded top-left canvas coordinates. Existing saved scenarios retain their locations.

## Documentation

Update/format/setup markdown notes are in `Updates/`; `README.md` and `requirements.md` remain in the project root. Links in the root documentation were adjusted accordingly.
