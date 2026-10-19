# Standard Work Sheet (SWS) / Combination Sheet (SWCS) — first draft

Reference sources supplied by the user:

- `F2 SWS.pptx` — tabular header/footer, workstation layout, material locations, route markings and operator paths.
- `HA Stage 4 Nozzle SWCS 031125 .xlsx` — operator-specific sheets showing step number, operation name, manual/automatic/walking time and colored time chart.

The source files are **reference examples only** and are not repackaged in this project. This implementation produces new editable documents with a similar layout rather than modifying the reference files.

## How to use

1. Update and validate the operator sequence in Line Builder.
2. Click **Run Simulation** to open the simulator.
3. Click **Export SWS (.pptx)** or **Export SWCS (.xlsx)** above the simulation canvas.
4. Review the drafts in PowerPoint / Excel. Re-export after edits to the line.

## SWS (.pptx)

- First slide: complete line layout, all operator routes and legend.
- Additional slide per operator: same layout emphasizing only their route.
- Stations, IN/OUT/SWIP boxes, numbered route stops and smooth route curves. Repeated stops at one point are consolidated as a numbered sequence with an offset badge and a leader line.
- Line Direction PNG arrows remain in the SWS, with their size, position, rotation, and flip settings preserved.
- Summary: line name (when available), takt, configured starting SWIP and operator count.
- Curved routes are editable PowerPoint freeform shapes approximating a Bézier curve.
- Routes connect configured operator standing points at stations and box centers. No aisle / obstruction routing is inferred.

## SWCS (.xlsx)

- One editable worksheet per operator, sorted by Op number.
- One row per sequence step (Pick, Work, Drop), plus return to home.
- Operation descriptions use the configured process names and locations.
- Manual and automatic time come from station processes. Walking uses the same station-side geometry and physical walking speed / layout scale as the simulator.
- Manual work and walking build an operator timeline. Automatic machine time starts after manual work and can **overlap** subsequent operator steps in its own separate row.
- The graphic uses native editable Excel shapes rather than painted-cell time bars: solid orange arrow = manual, purple zigzag arrow = walking, teal dashed arrow = automatic.
- The timeline is divided into 42 display divisions based on takt or the longest scheduled first-pass activity. Vector lines are positioned continuously across those divisions. Very short walking marks are expanded slightly for visibility; numerical times remain exact.

## Important limitations / follow-up iteration

- The exports use the planned operator sequence and station process times, **not the 100-takt playback trace**. They do not imply that blocking / idle or overlapping tasks have been validated by simulation.
- Detailed work elements, safety precautions, quality checkpoints, department, part number, framesize and scope may be unavailable in a basic saved scenario. Missing information is left blank / marked as not configured.
- Runtime steps are based on first-pass planned sequence. Automatic dwell is shown separately as machine activity and need not mean the operator is occupied throughout.
- The SWS full-line overview can be crowded on large multi-operator lines; the per-operator slides reduce clutter.
- Physical paths are straight-line travel **geometrically**, even though the visual connecting curves are smoothed for readability.
- No change to SQL Server storage or the scenario schema; both exporters use the latest simulated scenario in server memory.
- Install dependencies with `python -m pip install -r requirements.txt` after updating. `python-pptx` is now required for PPTX output.

## Code locations

- `standard_work_exports.py`: data mapping and generated PowerPoint / Excel documents.
- `app.py`: GET `/export-sws` and GET `/export-swcs` endpoints.
- `templates/simulate.html`: export controls.
- `static/js/playback.js`: enables controls after successful run.
- `static/simulation-dashboard.css`: export panel styling.
- `tests/test_standard_work_exports.py`: data and generated-document checks.
