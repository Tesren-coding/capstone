# Dashboard order and accessible playback timeline

## Dashboard
- Cards and shared navigation: **PQPR → Line Balancing → Line Builder**.
- PQPR and Line Balancing are labeled **In Development** but remain accessible.
- The public title is simply **Line Balancing**; the underlying Yamazumi visualisation module has not been removed.

## Simulation
- Playback-position slider, time readout and scrub instructions now appear **immediately below the simulation canvas**.
- The controls stay aligned with the canvas at desktop and mobile widths.
- The PLAY/PAUSE/RESTART, playback speed and back controls stay above the canvas.
- Playback seek / pause code and DOM element IDs are unchanged, so this is a presentational move, not a simulation behavior change.

No scenario storage or API migration is needed.
