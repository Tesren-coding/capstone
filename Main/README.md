# Capstone Line Planning Toolkit

## Install this update

Copy these files into the matching folders in your project. Keep your existing
`scenarios`, `pqpr_projects` and `balancing_plans` folders. Restart the Python app and refresh the browser (Ctrl+F5 if
an old interface is still cached).

Open PowerShell in the project folder:

```powershell
python -m pip install -r requirements.txt
python app.py
```

Open http://localhost:5000 in your browser to see the dashboard. Select
**Open Line Builder** to edit or simulate a line, or **Open PQPR** to plan
product/process applicability. Select **Open Line Balancing & Yamazumi** to
create an independent process list and assign its steps to operators. Existing `/builder` links
still open the builder directly.

For full Windows, macOS and Linux setup instructions, see `requirements.md`.

## Dashboard and planning apps: stages 1–3

The main page is a hub for three apps:

| App | Current availability |
| --- | --- |
| Line Builder | Available: the existing editor, scenario files and simulation. |
| PQPR | Available: projects, framesizes, shared processes, applicability, manual/auto timings and colors. |
| Line Balancing & Yamazumi | Available: independent process steps, optional PQPR import, assignments, manual-workload charts and plan files. |

Use the header navigation to move between apps. Returning to Line Builder in
this tab restores its draft. Save or export scenarios to retain them beyond
this session. `main.py` now opens the dashboard automatically.

`/` and `/dashboard` are dashboard URLs. `/pqpr` opens the PQPR editor;
`/line-balancing` opens the balancing editor. See `DEVELOPMENT_PLAN.md` for the staged feature and acceptance
plan. Scenario schema version 2 and event version 1 remain unchanged.

## PQPR projects

Name the project/line, add framesizes and shared processes, then check the
applicable matrix cells. Choose Always (P) or Sometimes (X) for checked steps.
Open **Edit shared processes** to set decimal manual/auto minutes and colors:
**green = in line**, **orange = out of line**, **blue = low hit rate / unique**.
Timings and colors are shared across framesizes in this version.

Process counts and nominal row timing totals update as you edit. Blank timing
fields mean unknown, and affected row totals show Incomplete. Sometimes steps
are included once in the counts/totals, without probability weighting.

Save/load projects in `pqpr_projects/`, with overwrite or numbered copies.
Import/export portable PQPR JSON. You can also import the supplied-style Excel
workbook and choose its CS/FS worksheet. P/X and recognized header colors are
retained; manual/auto times start blank and unsupported colors need review.
See `PQPR_FORMAT.md` for the full contract, import rules and timing assumptions.

Install updated requirements before running this release: Excel import adds
`openpyxl`. Scenario format 2 and event format 1 remain unchanged; PQPR uses its
own document type and format version 1.

## Line balancing and Yamazumi

Open Line Balancing and click **+ Process step** to add your own steps. Edit
names, categories, applicability and manual/auto minutes directly. Add named
operators and assign processes from the table or by dragging handles onto
operator lists or Yamazumi bars. Set takt time in minutes. PQPR import remains
optional under **Optional: start from PQPR**; its copied steps can be edited,
added to or removed independently.

Yamazumi bars stack manual work per operator in sequence order, with a dashed
takt line. Automatic process time is reported separately. Missing manual times
show incomplete workloads; unassigned steps and above-takt operators are
counted. Orange out-of-line steps are excluded by default, and Sometimes steps
can be toggled for the case being assessed. There is no hit-rate percentage
weighting yet.

Choose chart colors from PQPR categories or editable value-add tags. Hover or
focus a segment for details, drag it between operators or vertically to reorder work, click to find its
assignment row, or download
the chart as SVG. Balance efficiency and the manual-time minimum-operator
estimate are available when their required timings and assignments are complete.
The estimate does not include walking, waiting, precedence or machine capacity.

Save/load plans in `balancing_plans/`, with overwrite, numbered copies and
revision protection. Import/export self-contained plan JSON. Plans created from PQPR retain an optional
source copy: edits in the plan do not edit PQPR, and later PQPR changes do not
silently alter the plan. **Create plan** explicitly replaces the current plan
and prompts for unsaved changes. See `BALANCING_FORMAT.md` for calculations,
file fields and the workload assumptions.

PQPR is now connected to line balancing. Mapping the plan to physical stations
and generating a Line Builder scenario remains Stage 4.

## Code organization

HTML templates contain markup and one module entry point per page. JavaScript
uses explicit `import`/`export` dependencies; shared helpers are loaded by the
browser module system rather than globals or manually ordered script tags.

| File | Responsibility |
| --- | --- |
| `templates/` | Shared layout, dashboard and each app's markup. |
| `static/js/builder.js` | Builder state, placement, editor panels, import/export, save/load and launch. |
| `static/js/playback.js` | Playback clock, seeking, controls, tooltips and frame composition. |
| `static/js/api.js` | Shared JSON request handling. |
| `static/js/drag-sort.js` | Mouse/touch sorting, drag feedback and keyboard handle operations across apps. |
| `static/js/state.js` | Replay events into simulation display state. |
| `static/js/draw.js` | Draw canvas objects, banner and legend. |
| `static/js/positions.js` | Derive coordinates from the scenario. |
| `static/js/canvas-tools.js` | Shared zoom/pan, station text and helpers. |
| `app.py` | Line-builder web requests and application setup. |
| `planning_pages.py` | Dashboard, module registry and staged app entry pages. |
| `scenario_store.py` | JSON file revisions/save modes, with per-app validation. |
| `pqpr_routes.py`, `pqpr_store.py`, `pqpr_schema.py`, `pqpr_excel.py` | PQPR HTTP, persistence, validation and Excel import. |
| `static/js/pqpr.js`, `pqpr-model.js` | PQPR editing and display calculations. |
| `balancing_routes.py`, `balancing_store.py`, `balancing_schema.py` | Balance-plan HTTP, persistence, validation and workload calculations. |
| `static/js/balancing.js`, `balancing-model.js`, `yamazumi.js` | Balance editor, assignment operations, calculations and SVG chart. |
| `BALANCING_FORMAT.md` | Balance-plan contract and workload assumptions. |
| `scenario_schema.py` | Format versions, migrations and draft/run validation. |
| `simulation.py` | SimPy processing and material-flow rules. |
| `DATA_FORMAT.md` | Scenario/event contracts and future migration policy. |
| `tests/test_scenario_compatibility.py` | Repeatable compatibility, storage and route checks. |

Flask passes the part-image URL through the simulation canvas's
`data-part-image-url` attribute and format versions through the body data
attributes. Static JavaScript contains no Jinja expressions.

## Import, export and compatibility

Use **Import JSON** to choose a scenario from your PC. Supported older files
are upgraded in memory; the original file stays unchanged. Invalid or newer,
unsupported formats show a clear error and leave the current layout intact.
An imported scenario is a new unsaved layout. Save Scenario lets you name it;
existing-name conflicts still offer overwrite or a numbered copy.

Use **Export JSON** to download the current layout for another PC or a backup.
The downloaded file includes `schema_version: 2`. You can export/import drafts
before operator sequences are complete; Run Simulation checks the references
and sequence rules before calculating events. Imported metadata and extra
fields are retained when saving/exporting.

Unversioned and version-1 files are legacy inputs. Version-2 files must use the
process-list format. Future data-format changes need explicit migrations;
application bug-fix patches do not automatically change the scenario version.
See `DATA_FORMAT.md` for the fields, units, event meanings and release policy.

## Playback timeline

Use **PLAY**, **PAUSE** and **RESTART** to control playback. Restart returns to
the beginning and leaves playback paused. The speed dial changes viewing speed.

Drag **Playback position** backward or forward to inspect any recorded moment,
including a point between operator movements. Seeking pauses playback and
restores operator positions, carried and waiting parts, box counts, machine
phases and remaining times. Press PLAY to continue from the selected time.
The slider also supports the keyboard arrow keys when focused.

The time label shows elapsed / total simulated minutes. The timeline ends at
100 takt periods or at the first simulation error. At an error or completion,
seek backward to review and replay the preceding events. Seeking does not
change the scenario or its result; fix errors in the builder and run again.

## Station processes and machine times

Select a station to edit its list of processes. Each process has a name,
**Manual (min)** time and **Auto (min)** time. Decimal values are supported.
Both times must be nonnegative and their sum must be greater than zero.

Manual work requires an operator at the machine. Automatic operation begins
when manual work finishes and lets the operator move to another task. The
station stays occupied until the automatic operation finishes. A process can
be entirely manual or entirely automatic.

For example, a process with 1 minute manual and 4 minutes automatic time holds
the machine for 5 minutes while requiring the operator for the first minute.
The operator can perform work at another station during the remaining 4 minutes.

Add, rename, remove and reorder processes in the station editor. Each **Work**
step in an operator sequence selects the station and the process to execute.
Put multiple Work steps in the sequence if that part needs several processes
at the same station. Process list order controls the dropdown order; the
operator's Work-step order controls execution.

The manual/auto totals printed on a station sum all its configured processes.
They are not a measurement of operator utilization or the simulated line's
cycle time. Actual time depends on the selected work steps, walking and waits.

## Material movement and processing rules

- Each station holds one part and executes one process at a time.
- Dropping a new part at a station during manual or automatic processing stops
  the simulation with an error identifying the operator and station. The
  incoming part stays with the operator; the station's existing part is kept.
- An idle station that already holds a part also rejects another drop.
- Picking a part from a busy machine waits until its processing finishes.
- Starting the next process at that machine waits for the current process to
  finish. Manual work cannot start on an empty station or while carrying a part.
- Empty-source pickups and full-destination drops still stop with an error.
- Simulation time, machine state and animation use the same SimPy event stream.
  Walking time is included at the existing speed of 1000 layout pixels per
  simulated minute. Operators start from their configured positions and return
  there at the end of each sequence, then wait for their next takt period.
- Playback covers up to 100 takt periods and stops earlier on a flow error.

Station hover details show each process's manual/auto times, current machine
phase, current process, remaining time and whether the station holds a part.
The simulation draws a MANUAL or AUTO label during processing. Andon indicators
and Andon state have been removed.

## Existing scenarios

Older stations with only `cycle_time` load as one process with that duration
as manual time and zero automatic time. Old single-process Work steps are
linked to that process. Existing scenario files are only updated when saved.

If a referenced process is removed, affected Work steps are cleared and need
a replacement selected. Reordering processes or station IDs preserves valid
operator references.

## Previous controls retained

- Station IDs: apply a positive ID or drag the station-order list in the editor.
  Operator location and process references follow each station.
- Saving: overwrite, save a numbered version, or cancel. Loaded-file revision
  checks protect against overwriting a file changed since it was loaded.
- Canvas: scroll to zoom; Shift + left drag or middle mouse drag to pan;
  Reset view restores 100%. Works in both builder and simulation.
- Station names wrap with an ellipsis if needed; hover shows the full name.
- The current tab retains the builder draft when returning from simulation.
- The editor can be moved, resized, scrolled, or closed with its × button.

## Validation

Run the included automated checks after installing requirements:

```powershell
python -m unittest discover -s tests -v
```

These check legacy migration, unchanged input and simulation results, future
format rejection, migration sequencing, draft/run validation, save conflicts,
original-file preservation, import/export round trips and event versions.

Browser checks cover module loading, import/export and rejection without data
loss, metadata preservation, editing/reordering and ID references, save/load,
duplicate versions, draft restoration, zoom, simulation launch, machine
concurrency, tooltips, timeline restoration, pause/resume, restart, completion
and busy-transfer errors. Dashboard checks cover app navigation, available
module labels, responsive layouts and builder draft restoration. PQPR checks
cover applicable steps, P/X, time totals and missing values, category changes,
reordering/deletion, save/load/version copies, JSON round trips, metadata,
failed-import preservation, Excel selection/cancel and the reference worksheets.

Balancing checks cover source-copy ownership, framesize filtering, assignments
and sequence order, optional/out-of-line scope, decimal and unknown timings,
manual/auto separation, takt comparisons, efficiency, value colors, chart SVG,
save/load/copy/overwrite, metadata, rejected imports, draft navigation,
responsive layout and browser/backend calculation agreement.

Sorting arrows are replaced by ⠿ drag handles throughout PQPR, Line Builder
and Line Balancing. Drag PQPR process/framesize rows, station-ID order, station
processes, builder work steps, balance process rows, operators and assigned
work. IDs/references follow their records. Handles support Alt+Arrow keys.
Balance format 1 migrates to format 2 in memory; existing files are preserved
until explicitly overwritten. Pointer cancellation/outside drops make no edit.
