# Physical walking speed & assigned standing points

- New scenario-wide settings: `layout_scale_px_per_m` (default 50), `walking_speed_m_per_s` (default 1.2).
- Simulation walking duration in minutes = (layout distance / pixels per meter) / walking speed (m/s) / 60.
- Every operator Pick/Work/Drop step at a station may set `standing_side` (`top`, `right`, `bottom`, `left`). These points match the station snap slots: 26 canvas units beyond each station side.
- For steps with no side selected: use the operator's `attached_to` side when it matches that station; otherwise choose the nearest of four station access points from the operator's current position. This supports old saved layouts without migrations.
- Operators start and finish at their original saved home `x,y` (including their attached station position).
- `moving` events include `distance_m`, `walking_speed_m_per_s` for playback; the simulation times include walking time, not just a display conversion.
- Zoom only changes presentation, not physical distance.
- Calibrate the px/m scale to real station dimensions before treating results as measured walking times. This version computes Euclidean straight-line walking between access points and does not model aisle routing or collision avoidance.
- Global physical speed (m/s) is distinct from the simulation playback-speed multiplier (x).
- Old saved scenarios retain their layouts/attachments; when replayed with absent physical settings, the new default 50 px/m and 1.2 m/s apply. They may have different walking durations than the old 1000 px/min implementation.
