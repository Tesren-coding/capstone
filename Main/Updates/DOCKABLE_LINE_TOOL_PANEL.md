# Dockable Line Tool and Builder Layout

- The creation toolbar has been renamed **Line Tool** and includes station, SWIP, IN, OUT, operator, operator reordering, line direction, dimension, and cancel placement.
- Drag the Line Tool header to a canvas edge to dock to **left / right / top / bottom**. Left/right render a vertical stack; top/bottom render horizontally.
- Use the minus/plus button to collapse/expand the Line Tool. Dock placement and collapse state are remembered in browser localStorage (independent of the saved scenario).
- Line Settings and Run Simulation are below the canvas.
- Scenario file controls remain above the canvas. The Import JSON button is hidden, but its file input and existing handler remain for compatibility; the Download/Import fallback mode is still present.
- The Builder page header remains visible at the top while scrolling.

No schema changes, SQL migration, or changes to local-folder saves.
