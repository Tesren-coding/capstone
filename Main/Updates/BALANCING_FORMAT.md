# Line balancing and Yamazumi — format 2

Line Balancing is an independent dashboard app at `/line-balancing`. It owns
its process list, timings, classifications, operators and work sequences.
PQPR is an optional source of initial steps, not a required dependency.

## Workflow

1. Open Line Balancing and click **+ Process step**. Enter the name, category,
   manual/automatic minutes and Always/Sometimes case setting. Add as many
   steps as needed; blank timings remain unknown.
2. Add and name operators. Use the table's Operator dropdown, or drag a step's
   ⠿ handle onto an operator's work list or Yamazumi bar.
3. Set takt time in minutes. Drag a process-table handle onto another row to
   reorder the process catalog. Drag operator handles to reorder their cards
   and chart columns. These catalog/column orders do not change assignments.
4. Drag assigned step handles between operator lists or reorder within a list.
   Drag a Yamazumi segment between bars to reassign it. Within a bar, dropping
   in the lower half of a segment inserts before it; the upper half inserts
   after it. First work is at the bottom. Empty bar columns accept drops.
5. Drag work onto **Drop a work step here to unassign it**, or use × on its
   operator list. Unknown/zero-duration steps have no visible segment and can
   still be assigned and reordered through table/list handles and dropdowns.
6. Save/load plans, export/import JSON, or export the chart SVG. Remove a
   process to remove its assignments too. Step and operator IDs remain stable;
   deleted process IDs are not reused.

Handles support mouse and touch. **Alt+ArrowUp/Down** reorders the focused
handle; Left/Right is equivalent. Escape, pointer cancellation, or dropping
outside a valid target cancels without changing the plan. Reassignment via
Operator dropdowns is available without dragging. During dragging, scrolling
near the edge of the page or a scrollable list/chart reveals other targets.

Expand **Optional: start from PQPR** to load saved PQPR, its current-tab draft,
or a PQPR JSON file. Choose a framesize and create a plan. The source and its
IDs are copied as provenance. You may then independently add/remove/reorder
steps, change categories/applicability and edit times/names; PQPR stays unchanged.
Later PQPR changes do not update the plan. Creating another plan from PQPR
replaces the current steps and assignments and prompts for unsaved changes.

## C-shaped layout preference

The **C-shaped line and row break** panel previews one station per active
process. Incoming begins at top right; stations run left, turn down at the
chosen boundary, then continue right on the lower row to Outgoing.

Hover a gap between station tokens to preview the turn without changing data.
Click the gap, or drag the Row break marker to it, to commit the choice. Escape
cancels; the focused marker supports Alt+Arrow keys. The saved optional
`line_layout` record has shape `c` and `break_after_step_id` (a stable step ID or
null for the balanced default). Reordering follows that ID; removing its step
clears it. Fewer than two active steps have no selectable interior gap.

Build Line setup copies the preference. Its own C preview lets you adjust the
break between physical stations after grouping processes. Generation always
includes Incoming and Outgoing endpoint boxes, while the sequence mode still
controls whether Pick/Drop movement is proposed. See `BUILDER_SETUP_FORMAT.md`.

## Timing and calculations

All timing fields use minutes and may be decimal. Manual/auto times must be
nonnegative or `null` (unknown); takt is positive or `null` for an unfinished
plan. Zero is a known zero, distinct from a blank timing.

An active step is included in the case and either is not orange/out-of-line,
or the plan's include-out-of-line option is on. Exclusions retain assignments
so restoring the scope/case restores the assigned work.

| Result | Definition |
| --- | --- |
| Operator manual workload | Sum of active assigned steps' manual time; incomplete if any is unknown. |
| Automatic time | Separate process-time sum, incomplete if any active assigned auto time is unknown. It is not added to manual workload. |
| Manual / takt | Operator manual workload / takt × 100%. |
| Above takt | Complete operator manual workload exceeds takt (comparison tolerance 1e-9 minute). |
| Minimum operators | Ceiling of total active manual time / takt; with a tiny binary-rounding allowance at integer boundaries. Requires known times/takt. |
| Balance efficiency | Total active manual time / (number of operators × largest operator manual workload) × 100%. |
| Takt load | Total active manual time / (number of operators × takt) × 100%. |

Efficiency and takt load require all active steps to be assigned and manual
times to be known. All listed operators count, including empty ones. A zero
maximum workload has undefined balance efficiency. An operator with no active
steps is shown as **No steps**. Missing automatic time does not block an
otherwise complete manual workload comparison.

The minimum is a manual-time lower bound. Walking, waiting, precedence,
material movement and shared-machine capacity can require more operators.
Automatic operations may overlap, so their process-time sum is not elapsed
time or machine utilization. This stage does not validate a feasible machine
schedule or generate simulation sequences.

Sometimes steps are included once when selected, with no probability weighting.
Hit-rate percentage input remains a future feature. PQPR Always/Sometimes data
and its file version are unchanged.

## Chart and colors

The SVG chart shows known manual time only. **+ ?** identifies an operator
whose manual total is incomplete. Zero/unknown segments have no drawn height;
the process table and operator list retain them. A dashed line shows takt.
Hover or focus a segment for details; click or press Enter/Space to select its
assignment row. Long labels are shortened visually and retain full details.

Color mode **PQPR process category** keeps green/in-line, orange/out-of-line
and blue/low-hit-rate-or-unique meanings. **Value-add classification** uses
green/value added, yellow/semi value added, red/non value added and gray/
unclassified. Every step starts unclassified; PQPR category does not imply
value-add status. Classification edits belong only to this balance plan.

## Saved JSON

`document_type: "line_balance"` and `schema_version: 2` identify this format.
It is independent of scenario format 2, event format 1 and PQPR format 1.
Valid format-1 plans are checked under their original PQPR route rules and
upgraded in memory to format 2, preserving IDs, assignments, metadata and source.
Their original saved file is not rewritten until explicitly overwritten.
Unsupported future versions are rejected with an error without replacing the
current plan. A software patch does not require a schema change. Future
changes to field meanings need an explicit migration and compatibility tests.

Top-level fields:

| Field | Meaning |
| --- | --- |
| `plan_name` | Nonempty plan/line name. |
| `takt_time` | Positive minutes or null for a draft. |
| `source` | Optional `{project, filename, revision}` provenance copy, or null for independent plans (including plans with steps). |
| `framesize_id` | Selected framesize in the optional source, or null in independent plans. |
| `steps` | Independently editable process list in catalog order, including excluded steps. |
| `operators` | Ordered `{id, name, sequence}` records; sequence contains step IDs. |
| `next_operator_id` | Monotonic positive counter for new operator IDs. |
| `next_step_id` | Monotonic positive counter for new independent step IDs (`s1`, `s2`, …). |
| `include_out_of_line` | Whether orange processes are in workload scope; defaults false. |
| `chart_color_mode` | `process` or `value`. |
| `line_layout` | Optional `{shape: "c", break_after_step_id: <step ID or null>}`. |

Each step has `id`, `process_id`, `name`, `category`, `applicability`, `included`,
`manual_time`, `auto_time`, and `value_class`. `id` owns assignments; `process_id` is an optional source provenance ID (null
for new independent steps). A PQPR import initially uses the PQPR process IDs;
subsequent edits are not constrained to its original route. Required steps
stay included in the case, while the orange scope switch can exclude them from
this line. Optional steps can be toggled. Changing applicability to Always
sets included=true.
`value_class` is `unclassified`, `va`, `sva`, or `nva`.

IDs are stable; reordering does not change them. Duplicate assignments,
missing references, invalid times and invalid versions are rejected. Extra
metadata is retained during validation/import/export. Incomplete assignment
and timing records remain valid saveable drafts, with incomplete results
shown honestly in the UI.

## Storage and endpoints

Plans are saved in `balancing_plans/`, created when needed. The shared atomic
JSON storage supports create, overwrite, numbered copies and loaded-revision
checks. Imported JSON has no association with an existing saved plan. Browser
navigation retains a draft in this tab's session storage; save/export before
closing the session for durable copies.

| Endpoint | Purpose |
| --- | --- |
| `GET /line-balancing` | Editor and chart. |
| `POST /line-balancing/api/from-pqpr` | Validated source-to-plan copy for a framesize. |
| `GET /line-balancing/api/plans` | Saved plan filenames. |
| `GET /line-balancing/api/plans/<filename>` | Load plan and revision. |
| `POST /line-balancing/api/save` | Validated create/overwrite/duplicate with revision protection. |
| `POST /line-balancing/api/import` | Validate without saving. |
| `POST /line-balancing/api/export` | Portable JSON without saving. |
| `POST /line-balancing/api/analyse` | Validated workload calculations. |

Python's `balancing_schema.py` owns validation and backend analysis.
`balancing_routes.py` owns HTTP and `balancing_store.py` adapts shared storage.
Browser calculations and assignment operations are pure exports in
`static/js/balancing-model.js`; `yamazumi.js` renders SVG and resolves chart
drops; `drag-sort.js` provides shared pointer sorting and keyboard handles; `balancing.js` owns
page behavior. `templates/balancing.html` contains markup only.

`tests/test_balancing.py` checks independent plans, format-1 migrations, source copies, timing/scope
rules, incomplete results, duplicate assignments, revisions and round trips. Browser verification
also compares the browser's calculations with the backend on exported plans.
Stage 4 is available through **Build line from this plan**. It maps a copied
plan to physical stations, previews a new scenario, and requires material-flow
review in Line Builder. See `BUILDER_SETUP_FORMAT.md`.
