# Task-oriented operator assignments and cross-operator handoffs

## Motivation
Instead of requiring an operator to enter Pick, Drop, Work, Pick, Drop for every material movement, Line Builder now presents logical tasks:

- **Transfer part**: Collect from one material location and deliver to another, without processing.
- **Process part**: Work on an already-present or subsequently delivered part at a station.
- **Collect → Work → Deliver**: Collect a part, deliver it to the chosen station, work on it, then collect and deliver the processed part.

Different operators may perform these tasks for **the same part**. For example, Op1 transports a part from IN to S1, Op2 processes it at S1, and Op3 transports it from S1 to OUT. Station inventory is the shared handoff point. No operator-name or SQL schema changes are required.

## Editor
Select an operator in Line Builder. Use the three task buttons to add work cards. Select locations, workstation, and process for each card. Reorder tasks with the arrow buttons. For station processes, use **Choose side on canvas** to assign the existing station standing points. Box destinations remain at their center.

The *Advanced: individual Pick / Work / Drop actions* section preserves the old editor for atypical sequences and troubleshooting. Existing saved scenarios are interpreted as task cards where possible. Incomplete or nonstandard steps remain accessible as legacy actions; no data is silently deleted.

## Data and simulation
Tasks are a UI authoring layer. Each edit is compiled to the **existing `operator.sequence`** Pick / Drop / Work structure. This keeps the current simulation event stream, playback, SQL JSON persistence, save/load, and SWS/SWCS exports compatible.

The SimPy engine now waits for station parts to arrive before Work/Pick, and waits for station space before a Drop. It also allows a transfer to wait until a station's **assigned processing operations are complete** using the optional Pick field `wait_for_process: true`. New transfer/full-cycle tasks set this field by default; existing saved sequences without it keep their previous process-completion gating behavior. A SWIP box with no parts can wait for another operator to deliver one.

The process-completion condition uses the processes **assigned in all operators' sequences** at that station. It does not infer an optimal process order. If a configured handoff network cannot produce a needed part, an operator may wait until the simulation horizon. Out-of-line routes, capacity planning, deadlock detection, and obstacle-avoiding walking paths remain future work.

## Document exports
SWS and SWCS exports still read the compiled action sequence. They remain usable but continue to present their established action-level numbering and timing. A later export refinement can group those actions by logical task for cleaner standardized-work instructions.

## Verification
The task conversion and round-trip tests, browser workflow tests, existing Line Builder regression suite, operator-side snapping, and SWS/SWCS export tests pass in this workspace. Full SimPy and Flask end-to-end integration was not run because those dependencies are unavailable here. Live SQL Server integration was not tested.
