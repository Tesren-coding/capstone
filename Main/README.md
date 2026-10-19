## SQL Server Express storage (new)

Saved PQPR projects, Yamazumi plans, builder setups and line scenarios can now be stored in SQL Server Express. **See [SQLSERVER_SETUP.md](Updates/SQLSERVER_SETUP.md)** for Windows setup, SQL connection configuration, safe migration of existing JSON save directories, and verification. The default local JSON backend remains available until SQL mode is enabled with `CAPSTONE_STORAGE_BACKEND=sqlserver`.

# Capstone Line Planning Toolkit

**Simulation update:** Hover an operator in the canvas legend or the new operator chips to isolate their full assigned work area. See [Updates/OPERATOR_WORK_AREA_HIGHLIGHT.md](Updates/OPERATOR_WORK_AREA_HIGHLIGHT.md).

**Line Builder update:** Resizable station corners, live meter dimensions and a saved two-point **↔ Dimension** tool are documented in [Updates/STATION_RESIZE_DIMENSION_TOOL.md](Updates/STATION_RESIZE_DIMENSION_TOOL.md).

## Install this update

Copy these files into the matching folders in your project. Keep your existing
`scenarios`, `pqpr_projects`, `balancing_plans` and `builder_setups` folders. Restart the Python app and refresh the browser (Ctrl+F5 if
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

## Dashboard and planning apps: stages 1–4

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
`/line-balancing` opens the balancing editor. See `Updates/DEVELOPMENT_PLAN.md` for the staged feature and acceptance
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
See `Updates/PQPR_FORMAT.md` for the full contract, import rules and timing assumptions.

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
and prompts for unsaved changes. See `Updates/BALANCING_FORMAT.md` for calculations,
file fields and the workload assumptions.

Stage 4 connects balance plans to physical stations and generates a new Line
Builder draft. In Line Balancing, select **Build line from this plan**; in Line
Builder, use **Build a line from a balance plan**. The mapping editor also opens
directly at `/builder-setup`.

## Build a line from a balance plan

Choose a balance draft, saved plan or plan JSON. Map in-scope steps to physical
stations; several processes may share a station. Rename/add/remove stations
and drag their handles to change station order. Stations always generate in a
C-shaped path: Incoming at the top right, upper stations running left, then
lower stations running right to Outgoing. Save/load/export setups
in `builder_setups/` so the mapping can be reused.

In Line Balancing, hover station gaps in **C-shaped line and row break** to
preview the turn; click a gap or drag the Row break marker to save it. Adjust
the copied break in the setup page after grouping processes into physical
stations. Old plans without a marker use a balanced split.

Generate **Work steps only** for any operator count and complete material
movement in Line Builder. For exactly one active operator, you can choose a
proposed **IN → stations → OUT** sequence with input/output quantities. The
Incoming and Outgoing boxes are included in both modes. The transport
proposal follows that operator's work order and keeps consecutive processes
at one station together. Multi-operator handoffs are configured manually.

Generation rejects unknown timings, zero-total simulated processes, unassigned
steps and unmapped steps. Preview the station groups and operator sequences,
then export scenario JSON or open a new Line Builder draft. Opening prompts
before replacing dirty builder work and never saves over an existing scenario.

In Line Builder, review positions, Pick/Drop steps, buffers and starting parts,
then use **Check setup and mark reviewed** before running. Work-only drafts
without deliveries or starting parts cannot pass the review. Core edits make
the review stale. The simulation still checks actual machine/material flow.
Source plan/setup snapshots and IDs remain as provenance; later edits do not
silently change a generated scenario. See `Updates/BUILDER_SETUP_FORMAT.md`.

## Code organization

HTML templates contain markup and one module entry point per page. JavaScript
uses explicit `import`/`export` dependencies; shared helpers are loaded by the
browser module system rather than globals or manually ordered script tags.

| File | Responsibility |
| --- | --- |
| `templates/` | Shared layout, dashboard and each app's markup. |
| `static/js/builder.js` | Builder state, placement, editor panels, import/export, save/load and launch. |
| `static/js/playback.js` | Playback clock, seeking, controls, tooltips, summary updates and frame composition. |
| `static/js/simulation-metrics.js` | Planned initial SWIP and time-varying in-line WIP calculations. |
| `static/simulation-dashboard.css` | Responsive dashboard cards below the simulation canvas. |
| `static/js/api.js` | Shared JSON request handling. |
| `static/js/drag-sort.js` | Mouse/touch sorting, drag feedback and keyboard handle operations across apps. |
| `static/js/state.js` | Replay events into simulation display state. |
| `static/js/draw.js` | Draw canvas objects, banner and legend. |
| `static/js/positions.js` | Derive coordinates from the scenario. |
| `static/js/canvas-tools.js` | Shared zoom/pan, station text and helpers. |
| `app.py` | Line-builder web requests and application/blueprint setup. |
| `line_layout.py`, `static/js/line-layout.js` | Matching C-layout geometry and hover/click/drag break preview. |
| `builder_setup.py`, `builder_setup_routes.py` | Station mapping, plan-to-scenario conversion, setup storage and review HTTP endpoints. |
| `static/js/builder-setup.js` | Mapping editor, preview, setup files and new-draft handoff. |
| `planning_pages.py` | Dashboard, module registry and staged app entry pages. |
| `scenario_store.py` | JSON file revisions/save modes, with per-app validation. |
| `pqpr_routes.py`, `pqpr_store.py`, `pqpr_schema.py`, `pqpr_excel.py` | PQPR HTTP, persistence, validation and Excel import. |
| `static/js/pqpr.js`, `pqpr-model.js` | PQPR editing and display calculations. |
| `balancing_routes.py`, `balancing_store.py`, `balancing_schema.py` | Balance-plan HTTP, persistence, validation and workload calculations. |
| `static/js/balancing.js`, `balancing-model.js`, `yamazumi.js` | Balance editor, assignment operations, calculations and SVG chart. |
| `Updates/BALANCING_FORMAT.md` | Balance-plan contract and workload assumptions. |
| `scenario_schema.py` | Format versions, migrations and draft/run validation. |
| `simulation.py` | SimPy processing and material-flow rules. |
| `Updates/DATA_FORMAT.md` | Scenario/event contracts and future migration policy. |
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
See `Updates/DATA_FORMAT.md` for the fields, units, event meanings and release policy.

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

## Reorder operators in the Line Builder

The operator's **ID is also its name** (`Op1`, `Op2`, ...). To change which
operator occupies each numbered slot, click **↕ Reorder Operators** and drag
the ⠿ handle in the list. **Alt + Up/Down** reorders from a focused drag handle.
The list includes each operator's color and assigned locations so operators
remain distinguishable after renumbering. The top row becomes Op1.

Each operator keeps their color, position, station-side attachment, standing
point settings and work sequence. Reordering also closes gaps in older
operator IDs (`Op1`, `Op3`, etc.) by renumbering the resulting order.
There is no separate Renumber Operators button. Reordering supports
**Ctrl + Z** / **Ctrl + Y**, but does not alter a saved SQL scenario until you
choose **Save Scenario**.

## Simulation inventory & SWIP dashboard

A **Line Inventory & Flow** summary appears below the Simulation canvas after a
simulation loads. The starting SWIP cards count the **configured** initial
parts held by stations (`has_part`) and SWIP boxes (`has_part`):

- **Total Initial SWIP** = station starting parts + occupied SWIP boxes.
- **Total SWIP Boxes** = number of SWIP buffer boxes.
- **SWIP Boxes Starting With Parts** = number of occupied SWIP boxes (also
  shown as occupied / total).
- **SWIP Starting in Stations** = number of stations seeded with parts.

The live cards update during playback and timeline scrubbing: **Current In-Line
WIP** (stations + SWIP boxes + parts carried by operators), **Finished Goods
Output**, **Raw Material Remaining**, and **Simulation Time**. IN/OUT inventory
and Line Direction images are excluded from starting SWIP. The starting counts
are not a calculated minimum WIP required to sustain production; they reflect
how the scenario was configured. See `Updates/SWIP_FIRST_SIMULATION_DASHBOARD.md`.

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

Stage 4 checks cover shared physical stations, timing/work-order preservation,
scope exclusions, invalid/incomplete generation, mapping revisions/round trips,
new-draft ownership, canceled handoffs, review status/invalidation, source-file
preservation and a generated single-operator simulation through playback.

### Line Builder station alignment and operator snap points

New stations created manually or generated from Line Balancing / Builder Setup are
**150 × 96 canvas units**. The C-shaped layout and its preview share these
station dimensions; Incoming remains above-right and the row break is still
selected in the planning tools. Previously saved scenario station widths,
heights and positions are **not** automatically resized or realigned on import.

In Line Builder, press **+ Station** and move the pointer near an existing
station to see a snapping preview. New and dragged stations snap their edges,
centers or adjacent positions with a small gap, using a screen-relative
threshold that works at different zoom levels. Dragging empty space remains
possible away from nearby alignment points. When inserting on an occupied
station position, the builder proposes the nearest unoccupied adjacent slot.

Press **+ Operator**, or select an existing station/operator, to see dotted
operator-sized circles along the top, right, bottom and left sides of each
station. Click or drag an operator close to an unoccupied circle to attach it.
The circle center sits **26 canvas units** outside the station edge: a 16-unit
operator radius plus a 10-unit clear gap. Operators attached to a station
follow it when moved; dragging an operator away detaches it, while moving it
near another free circle attaches it there. Only one operator can occupy a
particular side anchor; freely placed operators may still overlap other items.

The optional operator field `attached_to` is stored as:

```json
"attached_to": {"station_id": "2", "side": "left"}
```

Attachments survive save/import/export, station ID swaps/reorders and older
v1/v2 scenario migrations. Deleting a station detaches its operators without
moving their final position. The scenario format remains **v2** because this
field is optional and does not alter the simulation data model.

**Tests:** `node tests/test_builder_snapping.mjs` tests canvas geometry and
zoom-aware snapping; `python -m unittest discover -s tests -p
"test_operator_attachments.py"` tests optional metadata and legacy geometry;
`python -m unittest discover -s tests -p "test_layout_geometry_standalone.py"`
tests generated C layouts. `python tests/browser_builder_smoke.py` tests the
real Line Builder canvas using Playwright and Chromium with a mocked HTTP API.
The complete app suite still runs via `python -m unittest discover -s tests -v`
when dependencies in `requirements.txt` are installed.
