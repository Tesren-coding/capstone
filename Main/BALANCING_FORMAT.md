# Line Balancing and Yamazumi: format 3

Line Balancing at `/line-balancing` owns a process catalog and a separate list
of assignable working elements. PQPR is an optional source of processes.

## Processes and working elements

A **process** is an operation such as Inspection. A **working element** is a
smaller step of that operation, such as Load part, Inspect or Unload part.

1. Add processes independently, or load a PQPR project and select a framesize.
   PQPR creates processes with that framesize's cell times, applicability,
   categories and parts per set. It does not create working elements automatically.
2. Click **+ Working element** on a process, or select its parent in the element
   toolbar. Enter element names and measured manual/auto times. A new element's
   manual time starts unknown and auto time defaults to 0; each belongs to a parent process.
3. If a process should remain indivisible, explicitly choose **Use as one
   element**. This copies its reference timings into one assignable element.
   Adding more elements afterwards requires editing those timings to represent
   the intended breakdown; the app does not infer a split.
4. Add operators and assign working elements through the table or drag handles.
   Drag elements between work lists or Yamazumi bars; drag within a bar/list to
   reorder work. First work is at the bottom of a bar. Empty bars accept drops.
5. Set takt in minutes per part, review workload, and save/export the plan.

Process reference times are shown beside their element sums. They are not
added to operator workloads. Only working-element times enter Yamazumi and
manual totals. Parts per set is product information; times and takt remain per
part and no quantity multiplication or batch scheduling is applied.

Process, working-element and operator lists have independent order. Drag
handles reorder each; Alt+Arrow provides keyboard sorting. Escape/outside
drops cancel. Operator sequences retain stable element IDs. Moving an element
to another parent preserves its assignment while updating its parent/category
and PQPR provenance. Removing a process removes its elements, assignments and
row-break references. Removing an operator leaves its elements unassigned.

A process or element can be Always or Sometimes. Always records stay included;
Sometimes records may be excluded. Orange work is outside scope by default.
An element is active only when both it and its parent are in scope. Exclusions
retain assignments. In-scope processes with no breakdown are reported as
incomplete, prevent complete whole-line metrics, and block scenario generation.

## Calculations and chart

Times are nonnegative decimal minutes. Blank manual time stays unknown (null);
blank, null or omitted automatic time defaults to 0. New processes/elements
start with auto time 0. Takt is positive minutes or null in an unfinished draft.

| Result | Definition |
| --- | --- |
| Operator manual workload | Sum of active assigned elements' manual time; incomplete if any is unknown. |
| Auto time | Separate sum of active assigned elements' auto time, using 0 for blank values. |
| Manual / takt | Manual workload / takt × 100%. |
| Above takt | Manual workload exceeds takt, using a 1e-9 minute tolerance. |
| Minimum operators | Ceiling of total active manual time / takt, with binary-rounding allowance. |
| Balance efficiency | Total manual / (operator count × largest manual workload) × 100%. |
| Takt load | Total manual / (operator count × takt) × 100%. |

Complete line metrics require every in-scope process to have elements and all
active elements to be assigned with known manual times. All listed operators
count, including empty ones. Automatic blanks default to 0 and do not block
known manual workload analysis. Zero maximum workload makes efficiency undefined.

Yamazumi draws known manual time only; **+ ?** identifies incomplete operator
manual totals. Zero/unknown elements remain editable and assignable through
tables/lists. Hover/focus segments for details; click to find the element row.
Colors follow process category or element value-add classification (`va`,
`sva`, `nva`, `unclassified`). Charts export as SVG.

The minimum is a manual-time lower bound. Walking, waiting, machine capacity,
precedence and material movement are not calculated. Auto sums are not elapsed
time or machine utilization. Sometimes work counts once when selected;
percentage hit-rate input remains deferred.

## C layout and station generation

The C preview shows one station per active parent process, in process order:
IN at top right, stations left to the break, down, then right to OUT. Hover a
gap to preview; click or drag the marker to commit. The preference uses
`line_layout: {shape: "c", break_after_process_id: "p1"}`; null defaults to a
balanced split. Stable IDs follow reordering, and deletion clears the hint.

Build Line setup initially groups a process's active working elements into
one physical station. Mappings can then be changed to split or combine physical
stations. Element IDs/times and operator work order are preserved in the
simulation's existing station-process and Work-step records. See
`BUILDER_SETUP_FORMAT.md` for review and transport requirements.

## JSON contract and compatibility

`document_type` is `line_balance`; `schema_version` is 3.

| Field | Meaning |
| --- | --- |
| `plan_name`, `takt_time` | Plan name and minutes per part. |
| `parts_per_set` | Positive whole-number product quantity. |
| `source`, `framesize_id` | Optional copied PQPR provenance and selected framesize; null for independent plans. |
| `processes` | Parent process catalog in physical route order. |
| `steps` | Working elements in editor order, including excluded elements. |
| `operators` | Ordered `{id, name, sequence}` records; sequences contain working-element IDs. |
| `next_process_id`, `next_step_id`, `next_operator_id` | Positive counters; new IDs use bp, s and o prefixes. |
| `include_out_of_line`, `chart_color_mode` | Scope and process/value color mode. |
| `line_layout` | Optional C preference with `break_after_process_id`. |

Each process has `id`, optional `pqpr_process_id`, `name`, `category`,
`applicability`, `included`, `manual_time`, `auto_time` (reference totals).
Each working element has `id`, required `balance_process_id` referring to its
parent, optional provenance `process_id`, `name`, `category`, `applicability`,
`included`, `manual_time`, `auto_time`, and `value_class`.

Names must be nonempty. IDs are unique within each list, browser safe and
stable. References must exist; an element can be assigned to at most one
operator. Manual timing values are finite nonnegative numbers or null.
Automatic null/missing values normalize to 0; invalid numbers/types are rejected.
Unknown extra metadata is retained. Unsupported newer versions are rejected.

Format-1 plans are first checked against their original PQPR route rules.
Formats 1 and 2 migrate in memory by adding one parent for each old step, keeping
all old step IDs, times, assignments and sequence order. Thus previous work
stays assignable and no breakdown is discarded. Old `break_after_step_id`
preferences are retained and translated to a parent marker. Copied PQPR
format-1 data also migrates. Original files are never rewritten on load/import.

Save/load uses `balancing_plans/` beside `app.py`, with overwrite, numbered
copies and revision conflict protection. JSON export/import is self-contained;
imports have no loaded-file overwrite association. Drafts persist in this tab.
PQPR and setup copies are independent: later source edits never silently update
plans or generated scenes. Creating a new plan from PQPR explicitly replaces
the current plan and prompts for unsaved work.
