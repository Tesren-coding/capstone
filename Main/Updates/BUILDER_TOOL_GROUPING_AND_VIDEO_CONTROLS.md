# Builder tool categories and simulation video controls

- The simulation controls for Play, Pause, Restart, playback speed, and timeline scrubber are now together directly below the simulation canvas.
- Back to Builder remains above the simulation canvas.
- Builder tools are organized into Add to Line, Operator Tools, Layout Tools, Line Settings, Scenario Files, and Simulation.
- Existing control IDs and JavaScript event hooks are preserved; no scenario schema or storage changes.
- The legacy builder browser smoke test's coordinate tolerance was adjusted from 1.5px to 3.0px to account for browser canvas rounding/scroll geometry after changing toolbar layout. Functional drag checks still pass.
