# PQPR projects: format and usage

The PQPR app at `/pqpr` manages a project/line name, shared processes and the
products/framesizes that use those processes. The matrix follows the supplied
PQPR workbook's framesize rows and process columns. It adds separate manual
and automatic timings and editable semantic colors.

## Use the editor

1. Name the project (usually the line).
2. Add framesizes and shared processes. Optional stage/component labels let
   you distinguish products with similar framesize names.
3. Open **Edit shared processes** to enter timings and select process colors.
4. Check each framesize/process intersection that applies. Choose Always (P)
   or Sometimes (X). Uncheck processes that do not apply.
5. Save the project locally on the server or export a portable JSON copy.

Process and framesize order can be changed using the editor's up/down buttons.
Stable IDs preserve checks through reordering. Removing a process confirms
removal of its applicability references. Editor counters avoid reusing its ID.

| Color | Stored category | Meaning |
| --- | --- | --- |
| Green | `in_line` | In-line process. |
| Orange | `out_of_line` | Out-of-line process. |
| Blue | `unique` | Low hit rate or unique process. |

Colors apply to shared processes, so a category change updates that process
across all framesizes. Color is a classification; it does not change a numeric
hit rate or weight cycle-time calculations.

## Timings and counts

Manual and automatic times are nonnegative decimal **minutes**. They are
shared per process in this version. A blank field is unknown (`null`), which
is different from an explicit zero. Both zero values and unknown values are
allowed while planning; a future generated simulation will need its own
stricter runnable validation.

Each checked process counts once toward a framesize's process count. Sometimes
steps are included in that count and separately identified. Row manual/auto
totals sum all checked processes once, including Sometimes steps. These are
nominal route totals, not expected hit-rate-weighted time, operator workload,
throughput, or elapsed time accounting for parallel machines. A missing time
in an included process makes that timing total Incomplete.

Repeated process names are allowed. Different columns have different stable
IDs, so separate visits such as Steam Clean remain separate steps. Global
column order determines the route order for each framesize after filtering
out its unchecked processes. Per-framesize timing overrides and independent
route orders are possible future extensions, not implemented in version 1.

## Save, load, import and export

**Save project** uses `pqpr_projects/`, separate from line-builder `scenarios/`.
It supports overwrite and numbered copies (`_v2`, `_v3`, etc.). Raw-file revision
checks protect against saving over a project changed since it was loaded.
Loading and importing never rewrite the original file. An imported file has
no overwrite association with an existing saved project.

**Import JSON / Excel** accepts PQPR JSON or a reference-style `.xlsx` workbook.
JSON import validates the document type, version, field types and references.
Invalid or unsupported newer files leave the current project intact. Unknown
extra metadata is preserved through JSON import/save/export. Line-builder
scenario JSON is a different document type and is rejected by this app.

For Excel, choose one worksheet when multiple PQPR sheets are found. The
importer expects a row with Frame/Framesize and Total Pieces headers, followed
by process columns, and product rows with P/X marks. It retains worksheet
column order, product names, stage/component labels and P/X applicability.
It does not evaluate volume or takt formulas, import equipment/hit-rate rows,
or treat them as manual/automatic timings. Repeated names remain distinct.

Header RGB/theme/indexed green, orange and blue colors are mapped to the three
categories. Unsupported colors, including the reference's yellow, default
to orange and are named in a review message. Always review categories after
an Excel import. Manual/auto times start blank because the supported reference
layout has no timing rows. The original workbook remains unchanged.

**Export JSON** downloads the complete current project, including timings,
categories and applicability. This release does not export an Excel workbook.
Drafts also persist in this browser tab while navigating among apps. Save or
export to keep a durable copy beyond the tab session.

## JSON contract: PQPR version 1

```json
{
  "document_type": "pqpr",
  "schema_version": 1,
  "project_name": "N2 repair line",
  "processes": [
    {"id": "p1", "name": "Inspect", "category": "in_line", "manual_time": 2, "auto_time": 0},
    {"id": "p2", "name": "Heat treat", "category": "out_of_line", "manual_time": 1, "auto_time": 20}
  ],
  "framesizes": [
    {"id": "f1", "name": "7HA.01", "stage": "2", "component": "Nozzle",
     "applicability": {"p1": "required", "p2": "optional"}}
  ],
  "next_process_id": 3,
  "next_framesize_id": 2
}
```

`project_name` and item names are non-empty text. `processes` and `framesizes`
are lists; they can be empty in a saved draft. IDs are unique within each list,
start with a letter and contain letters, digits, underscores or hyphens.
Browser-reserved IDs are rejected. `stage` and `component` are optional text
defaulting to empty strings. Timing fields are required numbers or null.

`applicability` maps existing process IDs to `required` or `optional`. Omitted
process IDs mean not used. Unknown referenced IDs are rejected. Unknown extra
fields are retained. Values must be valid JSON and all numbers finite.

The version is independent of scenario format 2 and event format 1. Future
PQPR format changes need explicit migration functions and compatibility tests
before increasing `PQPR_SCHEMA_VERSION`; newer unsupported formats are not
silently relabeled as version 1.

## Code and endpoints

| File | Responsibility |
| --- | --- |
| `pqpr_schema.py` | Validate versioned PQPR data and define route totals. |
| `pqpr_store.py` | Reuse the JSON storage/revision engine with PQPR validation. |
| `pqpr_excel.py` | Read reference-style Excel worksheets. |
| `pqpr_routes.py` | Module page and JSON/Excel HTTP endpoints. |
| `templates/pqpr.html`, `static/pqpr.css` | Editor markup and scoped styling. |
| `static/js/pqpr.js`, `pqpr-model.js` | Editing, file workflows and display calculations. |
| `tests/test_pqpr.py` | Contract, totals, persistence and import/export checks. |

API prefix: `/pqpr/api`. `GET /projects` lists saved filenames; `GET
/projects/<filename>` returns the project/revision. `POST /save`, `/import`
and `/export` accept a `project` object. Save accepts name/filename, mode and
optional expected revision. `POST /import-excel` accepts multipart `file` and
optional `worksheet`; it returns worksheet choices or an imported project.

## Tests

Run `python -m unittest discover -s tests -v`. The reference-workbook check
can be enabled by setting `PQPR_REFERENCE_XLSX` to its local path. The original
workbook is not redistributed inside the application ZIP.
