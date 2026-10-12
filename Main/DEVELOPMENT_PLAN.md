# Dashboard and planning apps: staged development

The application is becoming a Line Planning Toolkit. The existing line builder
is one app; PQPR and Line Balancing & Yamazumi are additional apps in the same
dashboard. New planning formats should have their own explicit versions and
link to scenarios through a deliberate conversion, rather than silently
changing existing scenario files.

## Stage 1 — Dashboard (completed)

- `/` and `/dashboard`: app dashboard.
- `/builder`: existing layout, station/process editors, scenario files and simulation launch.
- `/simulate`: existing simulation playback.
- `/pqpr`: the available PQPR editor added in Stage 2.
- `/line-balancing`: planned-module page describing operator assignments and Yamazumi.
- Shared navigation identifies the current app and marks planned apps clearly.
- `main.py` opens the dashboard. Existing `/builder` links still work.
- Builder drafts remain in the current tab when navigating through the dashboard.

PQPR is now available through Stage 2. Line Balancing & Yamazumi remains
planned; its editors and charts are not implemented yet.

## Stage 2 — PQPR: product/process routing (completed)

The project/line editor includes framesizes, optional stage/component labels,
shared process columns, Always/Sometimes applicability, manual/auto times,
and green/orange/blue categories. Counts and nominal timing totals derive
from checked processes. Blank times remain unknown.

Saved PQPR data uses its own version-1 contract and `pqpr_projects/` directory.
JSON save/load/import/export supports numbered copies and revisions. A
reference-style Excel importer offers a worksheet selector and preserves P/X
and recognized process colors; timings start blank.

Current definitions: each process column is one route step; repeated names
can have separate stable IDs. Each framesize filters the shared column order.
Timings and categories are shared per process; per-framesize timing overrides
and independently ordered route variants are future extensions. Row totals
include Sometimes steps once and are not probability-weighted workload.

Acceptance verified: multiple framesizes with different applicability,
reordering without lost references, category changes, decimal/unknown times,
save/load/copy, JSON round trips and the supplied CS/FS workbook layouts.
See `PQPR_FORMAT.md` for field definitions and importer limitations.

## Stage 3 — Line balancing and Yamazumi

Goal: list operators and the processes they perform, and show their workloads
against a selected takt time.

Select a framesize/route, define operator names, assign process steps and edit
their sequence. Use the applicable process timings to calculate workload and
draw stacked Yamazumi bars. Identify unassigned steps and workloads above takt.
Save assignments as a planning record referencing the product/process IDs.

Before building this stage, define whether bars represent operators, stations
or a selectable view; what time categories to show; and how automatic machine
time should be represented without treating it as operator attendance time.
Walking, waiting and overlapping work need explicit assumptions. A simple
sum of manual + automatic times is not automatically operator workload.

Acceptance: assignments survive save/reload; step order matches stack order;
totals match input timings; takt comparison is visible; automatic time is
identified according to the agreed workload definition.

## Stage 4 — Connect planning data to the line builder

Goal: turn a selected route and balancing plan into a reviewable starting
scenario for layout and simulation.

Map processes to physical stations, assign operators and generate Work steps.
Review material movement separately: a process route alone does not specify
pick/drop steps, input/output locations, buffers or starting parts. Preserve
source planning IDs as metadata so users can trace a generated scenario back
to its plan. Save a generated scenario as a new version/copy.

Acceptance: generation preserves selected processes and timings; references
are valid; incomplete movement setup is identified before running; changing
a plan does not overwrite a manually edited scenario without an explicit action.

## Architecture direction

`planning_pages.py` owns the dashboard, module registry and staged entry pages.
`app.py` retains existing line-builder HTTP endpoints and registers the PQPR
blueprint. PQPR uses separate templates, modules, schema and Excel-reader code;
its storage reuses the existing JSON/revision engine with PQPR validation. Future app features can
use separate Flask blueprints, templates, JavaScript modules and storage/schema
services. Shared services should be introduced when there is real shared data,
with documented ownership and migration rules.
