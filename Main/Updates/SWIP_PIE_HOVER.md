# SWIP Pie Hover and Callouts

- Only the starting SWIP pie chart and its legend remain below the simulation canvas.
- The static text caption for SWIP box counts has been removed.
- Hover a colored slice or legend row to emphasize the category and show a floating
  summary with the number of starting parts and the percentage of total SWIP.
- The tooltip additionally shows **SWIP boxes starting with parts: X of Y**.
- Hover or keyboard-focus the center of the pie to show the total and the box count.
- SVG leader lines and a dot identify the highlighted slice; unrelated slices are
  translucent. Keyboard tab/focus is supported on each nonzero segment and legend.
- The 100% case draws two SVG arcs so a scenario with just one SWIP category
  renders correctly. A zero-total scenario renders an empty grey pie.
- This is planned starting inventory, not a claim that it is the theoretical
  minimum SWIP needed to sustain a particular throughput.

Implementation: `templates/simulate.html`, `static/js/playback.js`,
`static/simulation-dashboard.css`. Test via
`python tests/browser_swip_pie_hover.py` and
`python tests/browser_simulation_metrics.py`.

### Targeted box occupancy hover
The detail **SWIP boxes starting with parts: X of Y** appears only for the SWIP-box pie segment or matching legend entry. Hovering station parts, IN-box parts, or the donut center still displays their own part totals but not SWIP-box occupancy.
