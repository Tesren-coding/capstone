# Empty SWIP pickups and per-operator waiting timeout

## Rules

1. **Pick from an empty SWIP box** stops the simulation immediately on arrival. An operator cannot wait for a part to be deposited into a SWIP box.
2. **Pick or Work at an empty station** may wait for another operator to deliver a part, but no longer than **five simulation minutes**, measured from the start of that specific blocked step. The timer belongs to that operator, not to the entire line, so progress by other operators does not extend it.
3. The five-minute timer counts time **blocked waiting for a required part**. Walking, manual processing, automatic operation, and normal between-cycle idle time are not counted as waiting for a missing part.
4. Existing immediate errors for occupied or busy stations, empty IN sources, and full destinations remain unchanged.
5. A wait that ends with delivery before five minutes succeeds and continues normally. If delivery never happens, a red `blocked` event names the operator, step, location and duration.

## Notes

This is an adjustment to runtime rules only. Scenario JSON format and task definitions are unchanged. The previous separate line-wide progress and output cadence checks remain; the line-wide watchdog will not preempt a blocked operator's five-minute timer with a generic stall message.

## Tests

`python -m unittest tests/test_simulation_stop_conditions.py` (run from the project root with SimPy installed). This suite includes empty SWIP, timeout at an empty station, output produced by another operator during a wait, and successful timely material delivery.
