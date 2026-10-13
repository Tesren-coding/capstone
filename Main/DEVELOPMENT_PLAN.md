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
through Stage 3. Stage 4 now connects planning records to physical simulation layouts.

## Stage 2 — PQPR: product/process routing (completed)

The project/line editor includes framesizes, optional stage/component labels,
shared process columns, Always/Sometimes applicability, manual/auto times,
and green/orange/blue categories. Counts and nominal timing totals derive
from used matrix cells. Manual/auto times are independent per framesize;
parts per set is a positive product quantity. Blank used manual times remain unknown; automatic blanks default to 0.

Saved PQPR data uses its own version-2 contract and `pqpr_projects/` directory.
JSON save/load/import/export supports numbered copies and revisions. A
reference-style Excel importer offers a worksheet selector and preserves P/X
and recognized process colors; manual timings start blank, automatic times 0.

Current definitions: each process column is one route step; repeated names
can have separate stable IDs. Each framesize filters the shared column order.
Categories are shared per process; timings belong to framesize/process cells.
Independently ordered route variants remain a future extension. Row totals
include Sometimes steps once and are not probability-weighted workload.

Acceptance verified: multiple framesizes with different applicability,
reordering without lost references, category changes, decimal/unknown times,
save/load/copy, JSON round trips and the supplied CS/FS workbook layouts.
See `PQPR_FORMAT.md` for field definitions and importer limitations.

## Stage 3 — Line balancing and Yamazumi (completed)

Create independent parent processes, or import a PQPR framesize with its cell
times and parts per set. Break processes into working elements with their own
manual/auto times. Importing PQPR does not automatically create working elements;
an explicit whole-process-as-one-element option is available. Add named operators and assign work. Each step belongs to at most
one operator. Drag handles and Yamazumi segments control assignments and work
order; deleting an operator makes its steps unassigned.

Yamazumi bars represent operators' manual workload only. Automatic process
time is listed separately; it is not treated as operator attendance. Timings
are editable copies. Unknown manual values stay unknown; automatic blanks
normalize to 0. Orange out-of-line processes
are excluded by default; optional Sometimes steps can be toggled per case.
A dashed takt line, above-takt counts, unassigned steps, balance efficiency and
a manual-time minimum-operator estimate support comparison. Walking, waiting,
precedence and machine capacity are outside this first workload calculation.

Colors can follow PQPR categories or manually assigned value-add classifications.
Charts export as SVG. Plans save/load/import/export in their own version-3
contract and `balancing_plans/` folder, with revisions and numbered copies.
An optional source PQPR copy retains provenance; changes in either app do not silently
modify the other. Browser navigation retains the current tab's balance draft.

Acceptance verified: source copies, framesize routes, assignment uniqueness,
work/stack sequence, manual and automatic totals, unknown timings, takt
comparison, optional/out-of-line scopes, chart colors/export, save/load/copy,
round trips and browser/backend calculation agreement. See `BALANCING_FORMAT.md`.

Format-1 and format-2 plans migrate by adding parents while preserving existing
working-element IDs, times, assignments and original files. Shared
pointer drag/keyboard sorting replaces sorting arrows in all three apps.
Station reorder remaps references simultaneously.

Hit-rate percentages remain deferred. Used PQPR cells retain Always/Sometimes;
time inputs replace inclusion checks, without probability-weighted workloads.

## Stage 4 — Connect planning data to the line builder (completed)

`/builder-setup` copies a selected balance plan, defines physical stations and
maps its active working elements. Each parent process initially uses one station;
elements can be remapped to split or combine stations; operator names,
source IDs, manual/auto times and in-scope work order are retained. Station
handles control station order. C-layout previews in both planning pages let
users hover/click/drag a row break. New scenarios always include Incoming at
top right, upper stations running left and lower stations running right to Outgoing. Setups save/load/import/export in their
own format-1 contract and `builder_setups/` directory with revisions/copies.

Generate a Work-only draft for any operator count. For exactly one operator
with active work, an optional serial IN → stations → OUT transport proposal
keeps consecutive same-station processes together and handles revisits.
Incoming/Outgoing boxes are included in both modes. Multi-operator Pick/Drop
handoffs, buffers and starting station inventory remain an
explicit material setup in Line Builder. Unknown/zero-total simulated times,
unassigned active steps and unmapped steps are identified before generation.

Preview/export does not write scenario files. Opening creates a new builder
draft, clears loaded-file association and prompts before replacing dirty work.
Source snapshots and per-record IDs retain provenance. Existing edited/saved
scenarios are unchanged unless explicitly replaced/saved through normal modes.

Generated scenarios require structural/material review before running. Core
edits invalidate review; Work-only drafts without deliveries or starting parts
cannot pass it. The simulation still detects actual flow failures. Existing
scenario formats and their previous run behavior remain compatible.

Acceptance verified: source/time/order preservation, shared stations, scope
omissions, references, setup revisions/round trips, canceled/applied handoff,
original-file preservation, review invalidation and a generated single-operator
scenario through simulation/playback. See `BUILDER_SETUP_FORMAT.md`.

## Architecture direction

`planning_pages.py` owns the dashboard, module registry and staged entry pages.
`app.py` retains existing line-builder HTTP endpoints and registers the PQPR, balancing and builder-setup
blueprints. PQPR uses separate templates, modules, schema and Excel-reader code;
its storage reuses the existing JSON/revision engine with per-app validation. Balancing has its own route, schema, storage adapter,
controller, pure model, chart renderer and stylesheet. Future app features can
use separate Flask blueprints, templates, JavaScript modules and storage/schema
services. Shared services should be introduced when there is real shared data,
with documented ownership and migration rules.

## Matrix timing and working-element update

Direct matrix process creation, per-framesize times and parts per set are
implemented. PQPR format 1 migrates to 2. Balance format 3 separates processes
from assignable working elements and avoids counting process totals twice.
In-scope processes without elements prevent complete whole-line metrics and
scenario generation. Parts per set is metadata; times/takt remain per part.
Acceptance checks cover migration, round trips, independent timings, parent
scope/deletion, workload calculations, physical grouping and generated simulation.
