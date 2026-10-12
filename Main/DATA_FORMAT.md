# Scenario and simulation-event formats

This is the contract shared by import/export, storage, the SimPy engine and
browser playback. Runtime validation and migrations live in `scenario_schema.py`.

PQPR projects use a separate version-1 contract documented in `PQPR_FORMAT.md`.
They are stored in `pqpr_projects/`, not in the scenario directory.

## Version policy

`CURRENT_SCHEMA_VERSION = 2` describes saved scenario data. It is independent
of software release numbers: a patch fixing a bug does not require a schema
change unless the meaning or structure of stored data changes.

| Input format | Handling |
| --- | --- |
| No `schema_version` | Treat as legacy version 1 and migrate. |
| Version 1 | Apply `migrate_v1_to_v2`, then validate. |
| Version 2 | Validate without pretending it is legacy data. |
| A higher version | Reject with a message to update the application. |
| Zero, negative, boolean, text or null version | Reject as invalid. |

Migrations operate on a deep copy. Loading and importing never rewrite the
original JSON file. Save writes the current format; an explicit overwrite
replaces the saved scenario, while a duplicate creates a numbered copy.
Export downloads the current format without writing to the server's scenarios
folder. An imported file has no overwrite association with an existing saved
scenario, even if its filename matches one.

Legacy `cycle_time` becomes process `p1` with that duration as `manual_time`
and `auto_time = 0`. If legacy `cycle_time` is absent, its existing default is
10 minutes. Numeric step locations become string IDs. A legacy Work step
without a process is linked automatically only when its station has one process.

For a future format change, increment `CURRENT_SCHEMA_VERSION`, register the
next migration in `MIGRATIONS`, update validation and this document, and add
compatibility tests. Retain earlier migrations so they can run in sequence.
Define intentional defaults and test that original inputs are unchanged and
old timings/references retain their meaning. Future releases must maintain
these migrations; they are not inferred automatically.

## Scenario version 2

All content must be valid JSON. Numeric values must be finite. Extra fields
are preserved through migration, import, save and export, including top-level
metadata. The simulation ignores fields it does not understand. Preserve the
schema version when adding optional metadata; use a new schema version for
changes that require different interpretation.

| Field | Meaning and rules |
| --- | --- |
| `schema_version` | Integer 2 for the current format. |
| `takt_time` | Positive number, in simulated minutes. |
| `stations` | Object keyed by positive integer string IDs, such as `"1"`. |
| `operators` | Object keyed by non-empty string IDs, such as `"Op1"`. |
| `boxes` | Object keyed by non-empty string IDs, such as `"IN_1"`. |

Missing object maps are normalized to empty maps. Station and box IDs cannot
overlap. Operator and box IDs `__proto__`, `constructor` and `prototype` are
reserved by the browser data structures.

Stations and boxes use `x` and `y` for the top-left corner in layout pixels;
`w` and `h` are positive widths and heights. Operator `x` and `y` are the
operator's center. All coordinates must be finite; negative coordinates are
allowed. Each station, box and operator needs a non-empty text `name`.

### Stations and processes

| Field | Meaning and rules |
| --- | --- |
| `has_part` | Optional boolean; missing means false. Initial occupancy only. |
| `processes` | Non-empty list of process objects. |
| Process `id` | Non-empty string, unique within that station. Stable reference. |
| Process `name` | Non-empty text. |
| `manual_time` | Nonnegative number of minutes requiring the operator. |
| `auto_time` | Nonnegative number of minutes after manual work; operator is released. |
| `cycle_time` | Derived sum of all process times, retained for compatibility. Not authoritative. |
| `next_process_id` | Optional editor counter used to avoid reusing removed IDs. |

A process's manual + automatic time must be greater than zero. A station
holds one part and runs one process at a time. Reordering the process list
changes its display order; operator Work-step order determines execution.

### Operators and steps

`color` is a list of three integer RGB values between 0 and 255. `sequence`
is an ordered list of steps:

| Step field | Meaning and rules |
| --- | --- |
| `action` | `pick`, `drop` or `work`. |
| `loc` | String ID of the target station or box. |
| `process` | Work steps select a process ID at the target station. |

Import, save and export allow drafts with empty sequences, blank selections
and unresolved location/process references. They still validate field types,
names, geometry, colors, process times and container shapes. Run Simulation
adds checks for valid references, at least one station/operator, non-empty
sequences and valid pick/drop/work ordering. This lets users preserve unfinished
layouts without presenting them as runnable scenarios.

### Boxes

| `type` | Additional fields and behavior |
| --- | --- |
| `in` | `start_count`: integer >= 0; starting supply. |
| `out` | `capacity`: integer >= 1; output hard cap. Starts at zero output. |
| `swip` | Optional boolean `has_part`; one-part buffer. |

## Event format version 1

`GET /events` returns `event_schema_version: 1`, the normalized `scenario`,
`takt_time` and an `events` array. The browser rejects an unsupported event
format rather than interpreting it using incompatible replay rules.

Each event has `time` (absolute simulated minutes from run start), `status`,
`operator` and `loc`. Operator/location can be null for global or home events.
Events are chronological; retain array order for events at the same timestamp.

| Status | Additional data and meaning |
| --- | --- |
| `moving` | `start`, `end` coordinates and `duration` in minutes. Interpolate position during travel. |
| `arrived` | `position`; movement ends at this location. |
| `pickup` | Part leaves source and becomes carried by the operator. |
| `dropoff` | Carried part enters the destination. |
| `manual_start` | `process`, `process_name`, `duration` (manual minutes), `auto_time`. Station busy; operator working. |
| `auto_start` | `process`, `process_name`, `duration` (automatic minutes). Station stays busy; operator can leave. |
| `operator_ready` | Operator released to the next sequence step. |
| `process_complete` | `process`; station becomes idle, with its part retained. |
| `waiting` | `reason`; operator waits for the station to finish. |
| `idle` | Operator waits for the next takt period after returning home. |
| `blocked` | `reason`; terminal flow error. Existing parts and carried parts remain in place. |
| `simulation_complete` | `reason`; terminal event after 100 takt periods. |

Walking speed is 1000 layout pixels per simulated minute. Manual work precedes
automatic work. A pick or next Work waits for a busy station; a drop into a
busy or occupied station fails. Runtime failures remain separate from format
validation because they depend on event timing and material availability.

`state.js` replays the same event stream the engine generated. Seeking rebuilds
the initial display state and applies all events through the selected time,
then interpolates any active movement. It changes viewing time only. The
machine countdown during manual work includes its remaining automatic time.

## HTTP interface and storage

| Route | Responsibility |
| --- | --- |
| `POST /import-scenario` | `{scenario: ...}`; validate/migrate and return an editable scenario without saving. |
| `POST /export-scenario` | `{scenario: ..., filename: ...}`; return current-format JSON without saving. |
| `POST /save-scenario` | Scenario, name/filename, mode and optional expected revision; save through `ScenarioStore`. |
| `GET /load-scenario/<filename>` | Return migrated scenario, source-byte revision and optional `migrated_from`; keep original bytes. |
| `GET /list-scenarios` | List saved JSON filenames. |
| `POST /delete-scenario/<filename>` | Delete the selected saved file. |
| `POST /launch` | Validate a runnable scenario and calculate its events. |
| `GET /events` | Return the latest run and its event-format version. |

Validation errors return HTTP 400 with `status: "invalid"`, `errors` and
`error`. Name conflicts, missing overwrite targets and revision conflicts
return HTTP 409. Revisions are SHA-256 hashes of the original saved bytes,
including when their in-memory representation has been migrated.

The JSON directory is relative to `app.py`, independent of terminal working
directory. The save lock coordinates this server process. The application
still holds one latest simulation per process; independent multi-user run
storage and coordination across server workers are separate future work.

## Verification

Run `python -m unittest discover -s tests -v` after installing requirements.
Tests cover migrations, input preservation, repeat normalization, unchanged
legacy simulation results, future-format rejection, ordered migrations,
draft/run validation, storage revisions, original-file preservation and
import/export round trips.
