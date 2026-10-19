# Scenario visibility and New Line recovery

- Running `python app.py` defaults to JSON unless `CAPSTONE_STORAGE_BACKEND` has been configured.
- JSON scenarios are read from `scenarios/` next to the **running** `app.py`. Personal save folders are not packaged into release ZIPs.
- To retain an existing JSON directory across extracted versions, set `CAPSTONE_SCENARIOS_DIR` to its absolute path before launching.
- The Load Scenario area shows the active backend, count and active JSON folder; errors are reported instead of silently rendering an empty list.
- A failed browser-session draft restoration is backed up under the `capstone-builder-draft-unrestored` sessionStorage key, then replaced with an editable blank line. New Line stays available while the draft restores.
- Neither fix deletes JSON files, modifies saved scenario contents, migrates SQL, or changes SQL table structures.
