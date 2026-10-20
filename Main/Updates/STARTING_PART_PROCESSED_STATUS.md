# Starting Station Part Status

## Scope
This update affects Line Builder station inventory and SimPy initialization only. It does not add process-route or PQPR validation and does not alter Line Balancing.

## Line Builder
Under a station's **Starts with a part** checkbox, choose one of:
- **Not Processed — needs station work** (default)
- **Already Processed — ready for transfer**

The selector is only visible when **Starts with a part** is checked. Clearing that checkbox resets the status to Not Processed. The selection is saved under the optional boolean station property `starting_part_processed`.

## Simulation semantics
- A **Not Processed** starting part has no completed station processes when the simulation starts. A collection step with completion waiting enabled must wait for required assigned station processing to finish.
- An **Already Processed** starting part is initialized with all processes assigned to that station by operator Work actions marked complete, so an operator may collect it immediately (unless the station is otherwise unavailable).
- **Every newly delivered part starts as Not Processed**, regardless of the starting part setting. The station completion set is reset when the station receives a new part.
- This is a station-level declaration, **not** proof that the part completed upstream production processes. Upstream dependency/route validation is deferred.
- A Work action deliberately assigned to an already processed starting part will correctly be treated as duplicate work by the existing simulation rules; configure the starting inventory/status to match the intended cycle.

## Backward compatibility
Existing scenario files without `starting_part_processed` default to `False` on a normalized copy. The original JSON file is never modified merely by loading. Scenario format version remains 2 and SQL schema is unchanged.

## Verification
- `python tests/browser_starting_part_status.py` checks selection, save/load, and resetting the status.
- `python -m unittest discover -s tests -p 'test_starting_part_status.py'` tests backward compatibility and field validation, plus three runtime tests when SimPy is installed.
- Existing Builder and standard-work export regressions have been checked; runtime tests need SimPy installed in the target environment.
