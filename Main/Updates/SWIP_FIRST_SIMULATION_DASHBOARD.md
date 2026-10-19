# SWIP-first Simulation Dashboard (2026-10-19)

## Changes

- Removed the standalone **Renumber Operators** button. **Reorder Operators** is the only operator re-ID action: drag or use Alt+Up/Down and the resulting list is numbered `Op1`, `Op2`, ... automatically. Existing operator identities and sequences are preserved by the reorder mapping, and undo/redo still works.
- Added an inventory and flow summary **beneath the Simulation canvas** (not on top of it):
  - **Total Initial SWIP**: one part for each station starting with a part + one part for each occupied SWIP box.
  - **Total SWIP Boxes**: number of boxes of type `swip`.
  - **SWIP Boxes Starting With Parts**: occupied SWIP boxes out of total SWIP boxes.
  - **SWIP Starting in Stations**: stations with `has_part` set to true.
  - **Current In-Line WIP**: parts held in stations, parts in SWIP boxes, and parts carried by operators at the current playback time.
  - **Finished Goods Output**: parts in all OUT boxes at the current playback time.
  - **Raw Material Remaining**: parts in all IN boxes at the current playback time.
  - **Simulation Time**: elapsed simulation minutes, including when scrubbing the timeline.
- The starting metrics stay fixed as playback advances; current metrics refresh when playing, seeking or restarting.

## Definitions and scope

The current data model has a boolean `has_part` for stations and SWIP boxes (one part maximum per such location). Starting SWIP is **configured initial work-in-process**, not a computed minimum WIP level required to keep the line running. Raw Material (IN), Finished Goods (OUT), and decorative Line Direction items do not contribute to initial or current in-line SWIP. WIP held by an operator counts as current in-line WIP.

No changes to the SQL Server Express JSON-document schema or its existing storage routes are required. More advanced line utilization requires explicit busy/idle timing definitions and is deferred to a later iteration.

## Main files

- `templates/builder.html`, `static/js/builder.js`
- `templates/simulate.html`, `static/simulation-dashboard.css`
- `static/js/simulation-metrics.js`, `static/js/playback.js`
- `tests/test_simulation_metrics.mjs`, `tests/browser_simulation_metrics.py`
- Existing operator tests updated to use **Reorder Operators** rather than the removed button.


## Current dashboard layout (Oct 2026)

The simulation canvas is followed by a single **Starting SWIP Breakdown** pie chart.
The displayed total has been expanded to include starting parts in **IN boxes**
(`start_count`) in addition to initially occupied stations and SWIP boxes.
The pie chart contains three segments (stations, SWIP boxes, IN boxes). The former
"During simulation" metrics row and the permanent SWIP-box caption are not
shown. They can be added again in a separate analytics implementation.

Hovering/focusing a segment or corresponding legend entry expands the segment,
dims the others, shows a pointer, and displays the segment count, percentage,
and `SWIP boxes starting with parts: occupied of total` in a tooltip. Hover or
focus the chart center to see total starting SWIP and the same SWIP-box count.
All annotations remain constant during playback and scrubbing because they
represent starting inventory.
