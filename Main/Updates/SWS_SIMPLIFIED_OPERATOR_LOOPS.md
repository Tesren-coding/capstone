# SWS: simplified repeatable operator loops

## Purpose

The shop-floor Standard Work Sheet should show a **repeatable operator visiting loop**, not every discrete Pick / Work / Drop event from SimPy. The simulation and SWCS still use the original detailed action sequences and walking-time data.

## Export behavior

- First assigned **workstation** is the operator's starting point (or first valid location for operators with no station tasks).
- A colored `Op1`, `Op2`, etc. **operator circle** is placed by that first workstation, using its configured standing point. Each operator's route still has its own slide plus the overview.
- Consecutive actions at the same place and **repeated visits to a location** appear once per diagram loop; the diagram is a schematic of locations that must be visited, not an event-by-event path.
- When a sequence starts at an IN/SWIP box and includes a station, show that initial supply box **at the end** of the repeated loop.
- Close the route with an arrow **back to the starting station**, not to the original canvas home/idle coordinates. If there is only one stop, show an operator marker with no spurious self-loop arrow.
- Number circular stop badges in route order; **do not** duplicate the starting station number at the end.
- Example: `SWIP -> S1 -> S2 -> idle` displays `S1 (Op1, #1) -> S2 (#2) -> SWIP (#3) -> S1`.
- Curved arrows and the editable PowerPoint shape markers remain, as do Line Direction, dotted IN/OUT/SWIP boxes, occupied-part icons and the original SWS template frame.
- The template's user-editable header, footer, legend and other existing shapes are kept **unchanged**.

## Limitation

The diagram deliberately simplifies repeat work. It is **not** a second simulation of travel times, aisle-based walking, operator picking/working chronology, or a work-instruction approval. All action-level details and timings remain available in the simulator/SWCS.
