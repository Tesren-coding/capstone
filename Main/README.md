# Capstone line building simulator

## Install this update

Copy these files into the matching folders in your project. Keep your existing
`scenarios` folder. Restart the Python app and refresh the browser (Ctrl+F5 if
an old interface is still cached).

Open PowerShell in the project folder:

```powershell
python -m pip install -r requirements.txt
python app.py
```

Open http://localhost:5000 in your browser.

## Station processes and machine times

Select a station to edit its list of processes. Each process has a name,
**Manual (min)** time and **Auto (min)** time. Decimal values are supported.
Both times must be nonnegative and their sum must be greater than zero.

Manual work requires an operator at the machine. Automatic operation begins
when manual work finishes and lets the operator move to another task. The
station stays occupied until the automatic operation finishes. A process can
be entirely manual or entirely automatic.

For example, a process with 1 minute manual and 4 minutes automatic time holds
the machine for 5 minutes while requiring the operator for the first minute.
The operator can perform work at another station during the remaining 4 minutes.

Add, rename, remove and reorder processes in the station editor. Each **Work**
step in an operator sequence selects the station and the process to execute.
Put multiple Work steps in the sequence if that part needs several processes
at the same station. Process list order controls the dropdown order; the
operator's Work-step order controls execution.

The manual/auto totals printed on a station sum all its configured processes.
They are not a measurement of operator utilization or the simulated line's
cycle time. Actual time depends on the selected work steps, walking and waits.

## Material movement and processing rules

- Each station holds one part and executes one process at a time.
- Dropping a new part at a station during manual or automatic processing stops
  the simulation with an error identifying the operator and station. The
  incoming part stays with the operator; the station's existing part is kept.
- An idle station that already holds a part also rejects another drop.
- Picking a part from a busy machine waits until its processing finishes.
- Starting the next process at that machine waits for the current process to
  finish. Manual work cannot start on an empty station or while carrying a part.
- Empty-source pickups and full-destination drops still stop with an error.
- Simulation time, machine state and animation use the same SimPy event stream.
  Walking time is included at the existing speed of 1000 layout pixels per
  simulated minute. Operators start from their configured positions and return
  there at the end of each sequence, then wait for their next takt period.
- Playback covers up to 100 takt periods and stops earlier on a flow error.

Station hover details show each process's manual/auto times, current machine
phase, current process, remaining time and whether the station holds a part.
The simulation draws a MANUAL or AUTO label during processing. Andon indicators
and Andon state have been removed.

## Existing scenarios

Older stations with only `cycle_time` load as one process with that duration
as manual time and zero automatic time. Old single-process Work steps are
linked to that process. Existing scenario files are only updated when saved.

If a referenced process is removed, affected Work steps are cleared and need
a replacement selected. Reordering processes or station IDs preserves valid
operator references.

## Previous controls retained

- Station IDs: apply a positive ID or use the up/down buttons to swap IDs.
  Operator location and process references follow each station.
- Saving: overwrite, save a numbered version, or cancel. Loaded-file revision
  checks protect against overwriting a file changed since it was loaded.
- Canvas: scroll to zoom; Shift + left drag or middle mouse drag to pan;
  Reset view restores 100%. Works in both builder and simulation.
- Station names wrap with an ellipsis if needed; hover shows the full name.
- The current tab retains the builder draft when returning from simulation.
- The editor can be moved, resized, scrolled, or closed with its × button.

## Validation

Checked process timing and machine concurrency, transfers during both phases,
early-pick waits, multiple process selection, legacy migration, fractional and
invalid times, reference updates, browser editing, save/reload, event playback,
hover details and busy-transfer errors. Browser checks found no missing assets
or page errors.
