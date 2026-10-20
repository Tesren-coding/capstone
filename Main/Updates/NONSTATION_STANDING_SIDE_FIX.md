# Standing side on SWIP/IN/OUT boxes — compatibility fix

## Problem

When an operator task's **Collect from** or **Deliver to** was changed from a station to an IN, OUT or SWIP box, the task editor previously retained its old `standing_side` value in the underlying Pick/Drop step. Running the scenario could fail with:

`Operator Op6, step 6: standing side can only be assigned at a station.`

Only stations have standing-side selections. The simulation uses the center of IN/OUT/SWIP boxes for walking destinations.

## Changes

- Task editor clears a previous location's side when **Collect from**, **Deliver to**, or **Workstation** is reassigned. Workstation changes also clear the full cycle's station pickup and dropoff sides.
- On load, restore, and before save/simulation, Builder clears obsolete standing-side settings on material-box steps. Operator tasks and existing station standing sides remain untouched.
- The backend scenario normalizer applies the same safe repair to its **deep copy**, so legacy files work whether they are opened through the web UI or sent to the server API. User files are **not rewritten automatically**.
- Invalid station standing sides and invalid location IDs still fail validation.

## Manual recovery without updating

If you cannot install the patch immediately, open Op6's **Advanced: individual Pick / Work / Drop actions**, identify step 6, and change its location to the desired box again (or remove the `standing_side` property from that step's JSON). Save a new scenario version before retrying.

## Validation

- `python -m unittest discover -s tests -p 'test_standing_side_normalization.py'`
- `node tests/test_operator_tasks.mjs`
- `python tests/browser_operator_tasks.py`

No SQL migration or save-format version change is required.
