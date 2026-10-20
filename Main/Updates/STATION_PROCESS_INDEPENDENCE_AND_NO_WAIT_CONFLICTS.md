# Independent station processes and immediate conflicts

## Updated simulation policy

- **Station processes are independent.** Being assigned to the same workstation
  does not make processes prerequisites of each other. The simulator no longer
  blocks collection simply because other station processes have not run.
- **Not Processed / Already Processed** remains on starting inventory. The
  setting tracks whether the station's *initial* part has had its assigned work
  completed, but does not block pickup. The simulator still prevents repeating
  the exact same process on the same part.
- **Delivery to occupied station**: immediately emits a `blocked` event; no
  waiting for the other part to be removed.
- **Delivery to busy station**: immediately emits a `blocked` event; no waiting
  for processing to finish.
- **Pickup/work while station is busy**: immediately emits a `blocked` event
  identifying the operator, sequence step and station.
- **Ordinary station pick/work on an idle, occupied station** remains valid.
  An operator must be able to visit a station with a part in order to process
  or collect that part.
- **Waiting for a missing part to arrive** at an empty station/SWIP is retained
  for legitimate cross-operator handoffs and is still subject to the existing
  stall/deadlock timeout.
- The old **Wait until station processing is complete** task-editor checkbox
  was removed. Legacy `wait_for_process` fields in saved JSON are accepted for
  compatibility, but have no runtime effect.
- No schema/storage migration. PQPR and Line Balancing are unchanged.

## Tests

`python -m unittest discover -s tests -p 'test_simulation_stop_conditions.py'`

`python -m unittest discover -s tests -p 'test_starting_part_status.py'`

`node tests/test_operator_tasks.mjs`

`python tests/browser_operator_tasks.py`

The Python runtime tests require SimPy (`python -m pip install -r requirements.txt`).
