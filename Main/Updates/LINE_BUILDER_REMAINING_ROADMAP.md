# Line Builder - future implementation backlog (20 October 2026)

This backlog is for **Line Builder and its simulation/export functions only**, not PQPR or Line Balancing.

## Highest value / next
- Refine original-template SWCS manually editable graphical work-combination symbols against actual workplace procedure and time axes. Preserve original template; currently shapes remain editable but do not automatically match newly calculated time intervals.
- Validate complete multi-operator SimPy behavior: handoffs, starvation, waiting, potential resource deadlocks and completed output in realistic test scenarios.
- Add simulation analytics: throughput, bottleneck, operator utilization (manual, automatic, walking, idle), station utilization, and line balance performance.

## Deferred (user explicitly asked to retain these as later suggestions)
- Automatically calculate **suggested SWIP inventory** and propose physical Kanban/box placements using routing, handoffs, walking distance, floor space, and iterative simulation. This requires production rules/assumptions and should be presented as suggestions rather than a claimed optimal result.
- SWS export boundary/print-preview overlay on builder canvas, with a readability warning for excessive reduction. Keep physical builder canvas unrestricted.
- Local project files on user's personal device for a server-hosted Flask app, with explicit file access consent, import/export fallback and recovery backup. Future `.capstone` project bundle could contain connected module data; no SQL or local persistence change is made by the SWS refinement.
- Multiple framesizes / alternate process routes, scrap/rework, quality impacts, and more accurate aisle/obstacle-based walking.

## Implemented / retained
- Task-based operator assignments compiled into Pick/Work/Drop actions; cross-operator handoff support; all-station operator standing points; operator IDs; move/resize/snap/dimensions/copy-paste; scenario JSON/SQL backends and recovery UI; curved SWS routes in the original editable PowerPoint frame; original imported SWCS Excel template; starting inventory SWIP chart.
