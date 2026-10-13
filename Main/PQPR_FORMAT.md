# PQPR projects: format 2

PQPR at `/pqpr` stores a project name, shared process columns and framesize
rows. A process is an operation such as Inspection; working elements are its
smaller steps, such as Load part, Inspect and Unload part.

## Matrix editing

1. Name the project and add framesizes.
2. Click **+ Process** in the matrix header or above the matrix. Name the new
   column directly and choose its color: green/in line, orange/out of line,
   or blue/low hit rate or unique.
3. Enter each framesize/process cell's manual and automatic time. Its cycle
   time is their sum. Times are decimal minutes **per part**.
4. A previously unused cell becomes used when either time is entered. Enter
   0 for no automatic operation; blank auto time also defaults to 0.
   Blank manual time in a used cell means incomplete. Use **Not used / clear**
   to remove a process from that framesize. Imported P/X cells retain membership
   even when manual time is unknown.
5. Set **Parts per set** for each framesize, in the matrix or framesize editor.
   It must be a positive whole number. New framesizes and old files default to 1.
6. Save the project or export JSON. **Balance this PQPR** opens the source
   selector in Line Balancing; choose a framesize to create its process catalog.

Used cells retain Always (P) or Sometimes (X). Percent hit rates remain deferred.
Process names and categories are shared across framesizes; actual cell timings
are independent. The process editor's timing fields are optional defaults for
newly used cells and never overwrite existing cells. Drag editor handles to
reorder processes or framesizes; Alt+Arrow is the keyboard equivalent. Stable
IDs retain timings and applicability. Removing a process also removes its cells.

Row totals include each used process once, including Sometimes processes.
They are per-part nominal sums, not elapsed time, machine utilization or
probability-weighted workload. An unknown included manual time makes the manual total incomplete.
Automatic totals use 0 for blank values. Parts per set is carried into balancing and generated scenario
metadata; it does not multiply per-part timings, takt, or simulation inventory.

## JSON contract

```json
{
  "document_type": "pqpr",
  "schema_version": 2,
  "project_name": "Repair line",
  "processes": [
    {"id": "p1", "name": "Inspection", "category": "in_line", "manual_time": null, "auto_time": 0}
  ],
  "framesizes": [
    {"id": "f1", "name": "7HA.01", "stage": "2", "component": "Nozzle", "parts_per_set": 12,
     "applicability": {"p1": "required"},
     "timings": {"p1": {"manual_time": 4, "auto_time": 2}}}
  ],
  "next_process_id": 2,
  "next_framesize_id": 2
}
```

`processes` and `framesizes` are lists, including empty lists for drafts.
Project and item names must be nonempty text. IDs are unique within each list,
start with a letter and contain letters, digits, underscores or hyphens;
browser-reserved IDs are rejected. Stage/component are optional text labels.
Categories are `in_line`, `out_of_line` or `unique`.

Process manual/auto fields are defaults. Each framesize's `timings` keys must
exactly match its `applicability` keys and refer to existing processes.
Applicability values are `required` or `optional`; omitted processes are unused.
Manual time is required in a used timing record: nonnegative finite minutes
or null when unknown. Automatic time is nonnegative finite minutes; null or
a missing value normalizes to 0. Negative, boolean and nonnumeric values are rejected. `parts_per_set` is a positive integer.
Unknown extra metadata is preserved through validation and JSON round trips.

Format 1 migrates in memory: every previously used cell receives an independent
copy of its process's timings, with blank auto time normalized to 0;
parts per set defaults to 1. Existing
routes, colors, order and metadata remain intact. Loading/importing never
rewrites the original file. Format 2 is validated as format 2; unsupported newer
versions are rejected. This version is independent of scenario/event formats.

## Files and Excel

Save uses `pqpr_projects/` beside `app.py`, with overwrite, numbered copies and
revision protection. Imports have no association with existing saved filenames.
Drafts stay in the current browser tab; save/export for a durable copy.

JSON imports validate type, version and references. Invalid imports leave the
current project intact. Excel imports accept the reference workbook layout:
Frame/Framesize and Total Pieces headers followed by process columns, product
rows with P/X marks, optional stage/component labels, and semantic header colors.
A worksheet selector appears for multiple PQPR sheets. Duplicate process names
keep separate IDs. Unknown colors default to orange with a review message.

The reference importer does not read cycle-time rows, parts-per-set quantities,
volume/takt formulas, equipment or hit rates. Imported used cells start with
unknown manual time, automatic time 0 and parts per set 1; review them in the matrix.
The original workbook is unchanged. Export is portable JSON, not Excel.
