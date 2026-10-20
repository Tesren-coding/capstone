# Simulation stop errors & navigation

This update changes only the **simulation runtime diagnostics** and the **simulation-page Back to Builder button location**. It does **not** change the operator task editor or how Pick/Work/Drop assignments are compiled.

## Runtime: every detected invalid or unresolved condition stops as an error

The simulator emits a terminal `blocked` event (time, operator, location, reason). Playback freezes at that event, disables Play, and displays a red error message beside the video controls. Restart resets the playback view; it does not fix the underlying scenario.

- Existing immediate stops retained: invalid pick/drop sequences; collecting an unavailable part; dropping without carrying; full IN/OUT/SWIP capacity where applicable; exhausted IN inventory; and invalid scenario definitions (reported at launch).
- **Station process completeness:** When an operator picks from a station, every process assigned to that station must have been completed on its current part. If `wait_for_process` is enabled the operator waits. If disabled, the run now **stops** if required processing is still incomplete; it will no longer silently transfer unfinished material.
- **Duplicate processing:** Repeating the same station process on the same part without part turnover is an error. Model legitimate rework explicitly rather than silently running the same process again.
- **Unresolved wait / starvation / deadlock:** Short handoff waits are legitimate. A watchdog stops the run if no part pickup, delivery, or processing progress occurs for `max(5 minutes, 3 × takt time)`. It reports waiting operator(s), locations and their reason(s). Detection reports a suspected deadlock/starvation from symptoms; it does not prove a formal cycle in a wait-for graph.
- **Output target:** Only scenarios with an explicit operator drop to an OUT box are checked. The first completed output has a startup allowance equal to the watchdog interval. Thereafter any gap between finished deliveries exceeding one takt period stops as **Output below takt target**. The watchdog also stops a run that fails to produce its next OUT delivery in time. This is deliberately strict and may need a configurable tolerance for real production batches.
- **No false success:** The 100-takt simulation horizon must not be labelled complete when operators remain waiting or required output has never been produced.

The errors are **scenario feedback**, not certified manufacturing validation. The simulator still uses straight-line walking and a simplified product/process model. Do not assume that a simulation's successful completion demonstrates process quality, safety or production feasibility.

## UI

- **Back to Builder** is now in the header of **Operator work areas**, immediately above the simulation canvas.
- A red, accessible error message appears under the playback controls when the stop event is reached. The page also previews the known stop reason and time at the top as soon as the precomputed event stream loads.

## Verification

- JavaScript test suite and relevant Builder/simulator browser regression tests passed.
- `simulation.py` and new backend test module compile.
- `tests/test_simulation_stop_conditions.py` covers missing material, empty SWIP, incomplete station work, duplicate work, below-takt output, and a valid flowing line. These require Flask/SimPy dependencies and **could not be executed in this offline environment**. Run `python -m unittest discover -s tests -p 'test_simulation_stop_conditions.py'` after installing `requirements.txt`.

No scenario file migration, database schema changes or new dependencies.
