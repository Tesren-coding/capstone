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
- `/line-balancing`: available balancing editor added in Stage 3.
- Shared navigation identifies the current app and marks planned apps clearly.
- `main.py` opens the dashboard. Existing `/builder` links still work.
- Builder drafts remain in the current tab when navigating through the dashboard.

PQPR is available through Stage 2; Line Balancing & Yamazumi is available
through Stage 3. Stage 4 connects planning records to physical simulation layouts.

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

## Stage 3 — Line balancing and Yamazumi (completed)

Create independent process steps with their own names, categories, manual/auto
times and applicability. Optionally import a PQPR framesize from saved data,
JSON or the current tab's draft, then add/remove/edit steps without route
constraints. Add named operators and assign work. Each step belongs to at most
one operator. Drag handles and Yamazumi segments control assignments and work
order; deleting an operator makes its steps unassigned.

Yamazumi bars represent operators' manual workload only. Automatic process
time is listed separately; it is not treated as operator attendance. Timings
are editable copies. Unknown values stay unknown. Orange out-of-line processes
are excluded by default; optional Sometimes steps can be toggled per case.
A dashed takt line, above-takt counts, unassigned steps, balance efficiency and
a manual-time minimum-operator estimate support comparison. Walking, waiting,
precedence and machine capacity are outside this first workload calculation.

Colors can follow PQPR categories or manually assigned value-add classifications.
Charts export as SVG. Plans save/load/import/export in their own version-2
contract and `balancing_plans/` folder, with revisions and numbered copies.
An optional source PQPR copy retains provenance; changes in either app do not silently
modify the other. Browser navigation retains the current tab's balance draft.

Acceptance verified: source copies, framesize routes, assignment uniqueness,
work/stack sequence, manual and automatic totals, unknown timings, takt
comparison, optional/out-of-line scopes, chart colors/export, save/load/copy,
round trips and browser/backend calculation agreement. See `BALANCING_FORMAT.md`.

Format-1 plans migrate without changing source files or assignments. Shared
pointer drag/keyboard sorting replaces sorting arrows in all three apps.
Station reorder remaps references simultaneously.

Hit-rate percentages were explicitly deferred. Always/Sometimes remains the
PQPR input, without probability-weighted workloads.

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
`app.py` retains existing line-builder HTTP endpoints and registers the PQPR and balancing
blueprints. PQPR uses separate templates, modules, schema and Excel-reader code;
its storage reuses the existing JSON/revision engine with per-app validation. Balancing has its own route, schema, storage adapter,
controller, pure model, chart renderer and stylesheet. Future app features can
use separate Flask blueprints, templates, JavaScript modules and storage/schema
services. Shared services should be introduced when there is real shared data,
with documented ownership and migration rules.
