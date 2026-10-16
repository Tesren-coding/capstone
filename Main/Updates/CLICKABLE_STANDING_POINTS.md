# Clickable operator standing-point assignment

## Interaction

- Select an operator with station steps in its sequence. The first assigned station step is active by default.
- **Only the active step's station** displays four dotted standing circles (top, right, bottom, left).
- Click one of the circles on the canvas to assign where the operator will stand for **that step**.
- If the sequence has other station steps, click **Select on canvas** alongside the desired step to show that station's four circles instead.
- Use **Use Auto** to remove the explicit `standing_side` property. Auto chooses the operator's attached home side for that station, otherwise the nearest side.
- Station selections and box-only sequence steps do not show standing circles.
- The operator's home attachment can still be dragged independently; side selection does not move the permanent home icon.

## Walking distance

- The simulation retains `layout_scale_px_per_m` and `walking_speed_m_per_s`.
- Station destinations use the per-step `standing_side`, or automatic station-side logic for older saves.
- **IN, OUT and SWIP boxes always use their center** as destinations, even when operators stand at a station side.
- World canvas geometry, physical walking calculations and data schema remain unchanged. No SQL migration is necessary.

## Files

- `static/js/builder.js` — new canvas selection UI; no standing dropdown.
- `walking_geometry.py` / `simulation.py` — explicit testable box-center destination helper.
- `tests/browser_walking_points.py` — browser interaction and persistence tests.
- `tests/test_physical_walking.py` — box center and physical walking tests.
- `tests/browser_multiselect.py` — confirms unassigned operators show no standing-point rings.
