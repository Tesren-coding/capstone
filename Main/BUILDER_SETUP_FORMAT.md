# Stage 4 — balance plan to Line Builder

Stage 4 provides a mapping editor at `/builder-setup`. Open **Build line from
this plan** in Line Balancing, or **Build a line from a balance plan** in Line
Builder. It converts a copied balance plan into a new, reviewable scenario.
PQPR is optional: independent balance plans work identically.

## Workflow

1. Choose the current tab's balance draft, a saved balance plan, or imported
   balance JSON. The setup stores a validated copy; later plan edits do not
   silently change it. To use a changed plan, explicitly load it again and
   create a new mapping. Unsaved setup changes prompt before replacement.
2. Name the setup/scenario. Define physical stations and map each active
   process to one station. The initial mapping uses one station per step;
   several steps can be mapped to the same station. Rename/add/remove stations.
   Removing a mapped station clears its mappings so they must be reassigned.
3. Stations always generate in a C-shaped path: Incoming at the top right,
   stations running left to the selected break, then continuing on the lower
   row from left to right, ending at Outgoing. Drag station handles to change
   station order; IDs and mappings remain stable. Move/zoom the generated
   layout in Line Builder to represent your intended physical spacing.
4. Choose a starting sequence and generate a preview. Review station/process
   groups and each operator's proposed work. Export scenario JSON or open a
   new Line Builder draft. Editing mappings/settings invalidates the preview;
   regenerate before exporting/opening the updated setup.
5. In Line Builder, review physical positions, timings, operator sequences,
   Pick/Drop handoffs, buffers and starting parts. Use **Check setup and mark
   reviewed**. Then run simulation to test actual material/machine flow.
6. Save the generated scenario under a new name or numbered version.

Setups save/load in `builder_setups/`, with overwrite, numbered copies and
revision conflict checks. Setup JSON import/export is portable. Browser
navigation retains the current tab's setup draft; save/export before closing
the session for a durable copy.

## Selecting the C-shaped row break

In Line Balancing, the **C-shaped line and row break** panel shows one station
per active process. Glide over a gap in the station strip to preview a different
turn. Hovering does not edit the plan. Click a gap to save it, or drag **Row
break** onto a gap and release. Escape/outside drops cancel a drag. Focus the
marker and use Alt+Arrow keys for keyboard placement. The strip stays fixed
while the C-shaped preview changes so the target does not move under the mouse.

The break is saved as optional `line_layout: {shape: "c",
break_after_step_id: "s3"}` in balance format 2. The referenced ID follows its
step through reordering. Excluded steps retain the hint; removing that step
clears it. Without an available interior hint, a balanced split is used.

Creating a setup copies the hint to `layout: {shape: "c",
break_after_station_id: "3"}`. Its preview uses mapped physical stations;
several processes sharing a station cannot be split across rows. Adjust the
break here after grouping/reordering. An unavailable or last-station marker
falls back to a balanced interior split, with a generation note. Choosing a
new break invalidates the existing generated preview until regenerated.

The upper stations decrease in X; the lower stations increase in X. The last
upper and first lower station share X. Each row keeps the same spacing; uneven
station counts produce different arm lengths. Incoming sits immediately right
of the first upper station; Outgoing sits right of the last lower station.
A single station sits on the upper row with Outgoing below/right. No manual
station movement is needed to create the initial C.

Older plans/setups without layout fields still import and default to C on new
generation. Existing scenario files keep their saved coordinates until the
user explicitly generates/opens another draft. Plan, setup and scenario format
versions remain unchanged because the saved layout preferences are optional.

## Two sequence modes

**Work steps only** supports any number of assigned operators. Each operator
keeps its in-scope balance work order, with station/process references filled
in. Incoming and Outgoing boxes are always included at the C-shaped endpoints,
with the configured input count/output capacity. Pick/Drop steps and station
starting parts are not inferred. Add the material handoffs in Line Builder. A Work-only draft without deliveries or starting
parts cannot be marked reviewed or launched.

**Single operator — proposed transport** requires exactly one operator with
in-scope work. It creates an IN box and an OUT box and follows that operator's
work sequence:

- Pick from IN and drop at the first station.
- Perform consecutive processes at the same station without moving the part.
- On a station change, pick from the previous station and drop at the next.
- After the last process, pick and drop at OUT.

Revisiting an earlier station creates an explicit return. The proposal does
not invent a new product route: its order comes from the operator's balance
sequence. Review that order against the intended repair/production route.
Input count defaults to 150 and output capacity to 200, both editable. Stations
start empty. Pick and Work waits use the existing simulation's machine rules.

Multi-operator transport is not inferred. Who carries a part, where it waits,
which buffers start full, and when each operator can pick it up must be
specified in Line Builder. A balance chart alone does not establish those
handoffs or prove a feasible schedule.

## Generation checks and ownership

Generation requires positive takt, at least one active process, all active
steps assigned to operators, all active steps mapped to valid stations, and
both manual/auto times known and nonnegative with positive combined processing
time. A known zero manual or auto time is valid; blank is not silently zero.
Setups with incomplete mapping/assignment/timing can still be saved as drafts.

Active scope uses the balance plan's case and include-out-of-line option.
Excluded Sometimes/out-of-line steps are omitted from the scenario but remain
in the embedded source copy. Unused physical station definitions and operators
with no in-scope work are omitted, with notes in the preview.

A physical station can hold multiple processes, each retaining its balance
step ID, name, manual/auto times, category and value-add tag. Operators retain
names, work order and source IDs; generated simulation IDs are `Op1`, `Op2`, …
so the existing builder can add further operators normally.

`planning_origin.setup_snapshot` stores the copied plan, its optional filename/
revision, initial station definitions, mappings and generation mode. Station
processes also carry `source_step_id` and optional `source_process_id`;
operators carry `source_operator_id`. Provenance is a historical snapshot.
Later builder edits do not edit the plan/setup, and station/process metadata
travels with its records when the builder reorders them.

Preview and export do not save a scenario file. Opening a generated draft
resets the builder's loaded-file association. Dirty builder work prompts
before replacement; cancel keeps it and leaves a notice to open/discard the
queued generated draft later. Existing saved scenarios are never overwritten
by generation or handoff. Normal Save Scenario modes still apply afterward.
If browser storage is full, export the generated scenario JSON and use Line
Builder's Import JSON.

## Material-flow review

Generated scenarios contain `planning_origin.material_review_required: true`
and initially have no review fingerprint. Run/launch validation rejects these
until reviewed. The review endpoint checks normal runnable references and
sequence carrying rules, identifies a Work-only draft with no deliveries or
starting parts, and records a fingerprint of the normalized core scenario.

Changing takt, stations/processes, operators/sequences, boxes/inventory or
layout makes that fingerprint stale and requires another review. Review
status survives save/load/import/export and browser navigation when the core
scenario is unchanged. Source/provenance notes alone do not invalidate it.

These are structural checks and an explicit user review, not proof of a
feasible flow. The simulation continues to detect busy drops, empty pickups,
full boxes and other runtime problems. Initial coordinates use the existing
pixel-based walking model; set layout and assumptions deliberately before
using the result to judge a real line.

Existing scenarios with no generated-review metadata keep their previous
validation/run behavior. Scenario format remains 2; event format remains 1;
balance format remains 2; setup uses its own format 1.

## Setup JSON format 1

| Field | Meaning |
| --- | --- |
| `document_type` | `builder_setup`. |
| `schema_version` | `1`; unsupported versions are rejected without replacing current data. |
| `setup_name` | Nonempty name, carried into scenario metadata/suggested filename. |
| `source` | `{plan, filename, revision}`; validated balance copy and optional saved-source reference. |
| `stations` | Ordered `{id, name}` definitions; unique positive integer string IDs and nonempty names. |
| `mapping` | Active step ID → station ID; missing/empty mappings are allowed in a setup draft. |
| `next_station_id` | Positive monotonic counter; deleted IDs are not reused. |
| `mode` | `work_only` or `single_operator_flow`. |
| `input_count` | Positive integer for the Incoming box in either mode; defaults 150. |
| `output_capacity` | Positive integer for the Outgoing box in either mode; defaults 200. |
| `layout` | Optional `{shape: "c", break_after_station_id: <station ID or null>}`; null/missing uses a balanced row break. |

Unknown metadata is preserved. Mappings cannot refer to excluded/unknown
steps or nonexistent stations. Converter output is validated as a draft
scenario using the shared scenario contract before it reaches Line Builder.

## Code and endpoints

`builder_setup.py` owns the format, mapping validation and conversion.
`builder_setup_routes.py` owns the blueprint and SetupStore adapter over shared
atomic JSON/revision storage. `templates/builder_setup.html` is markup;
`static/js/builder-setup.js` controls the editor and handoff. `line_layout.py`
provides converter geometry; `static/js/line-layout.js` provides matching
preview geometry and hover/click/drag break controls. Shared drag/API
helpers are reused. Core generated-review validation lives in
`scenario_schema.py`, used by launch, simulation and review routes.

| Endpoint | Purpose |
| --- | --- |
| `GET /builder-setup` | Mapping editor. |
| `POST /builder-setup/api/from-plan` | Copy a validated balance plan into an initial setup. |
| `GET /builder-setup/api/setups` | Saved setup filenames. |
| `GET /builder-setup/api/setups/<filename>` | Load setup with revision. |
| `POST /builder-setup/api/save` | Create/overwrite/duplicate setup. |
| `POST /builder-setup/api/import` | Validate setup without saving. |
| `POST /builder-setup/api/export` | Portable setup JSON without saving. |
| `POST /builder-setup/api/generate` | Validate mappings and return scenario draft/notes, without saving. |
| `POST /builder-setup/api/review-status` | Report whether the current generated core matches its review. |
| `POST /builder-setup/api/review` | Structural validation and recording of explicit setup review. |

`tests/test_builder_setup.py` covers source ownership, shared stations, IDs/
timings/order, scope exclusions, invalid/incomplete setup, single-operator
transport including revisits, review invalidation, actual simulation, round
trips, numbered versions, revision conflicts and server-side launch checks.
Browser checks also exercise the source link, mapping editor, canceled/applied
handoff, original-file preservation, new-file saving and playback.

`tests/test_line_layout.py` checks C directions/endpoints at every interior
break, single-station/default layouts, old-file handling, grouping, preserved
assignments/timings, invalid preferences and actual C-layout simulation.
Browser tests compare Python and JavaScript geometry, verify hover-only
preview versus committed placement, and save/reload break preferences.
