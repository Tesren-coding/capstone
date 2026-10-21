# Operator Wait task (intentional inactivity)

## Builder

- Select an operator in Line Builder.
- In **Operator tasks**, click **+ Wait**.
- Set **Wait duration (simulation minutes)** to a positive number (fractions allowed, such as 0.5).
- Reorder the task alongside Transfer, Process and Full Cycle tasks.
- The saved low-level step is `{ "action": "wait", "duration": 5 }` (no location required).
- Existing JSON scenario files and local-device-folder saving remain compatible.

## SimPy semantics

- When the Wait task starts, the operator remains at their current position for exactly the configured amount of **simulation time**.
- They neither move nor handle parts nor start processing during that interval. The operator may remain carrying a previously picked part.
- The event stream emits `planned_wait_start` and `planned_wait_end`. Playback presents the operator as idle, with no movement.
- **Deliberate Wait tasks are excluded from the 5-minute blocked-handoff timer** and from the generic no-progress watchdog while the pause is active.
- Other operators and already-started machine automatic cycles may continue while this operator waits.
- A configured finished-output takt target still applies when an operator delivers finished parts to OUT; inserting Wait does not waive takt performance checks.
- Waiting indefinitely for an unavailable part is NOT a Wait task and retains the existing 5-minute stop error.

## Exports

- SWS movement paths do not gain a new station or travel arrow for Wait.
- The SWCS written task list includes a `Wait / idle for ... min` row. The original template's editable drawn timing lines remain unchanged for manual review.

## Verification

- Task compiler roundtrip and default creation tested with Node.js.
- Chromium editor tests cover adding/editing Wait, advanced action editing, and scenario roundtrip.
- Python validation and SWS/SWCS export tests passed.
- Full SimPy runtime tests are included in `tests/test_operator_wait_task.py` but cannot execute without SimPy installed. Run with `python -m pip install -r requirements.txt` in your environment.
