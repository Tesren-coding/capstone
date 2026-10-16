# Line Builder — Rename Scenario

The **Rename Scenario** button is next to **Load Scenario**.

1. Select a saved scenario from the dropdown.
2. Click **Rename Scenario** and enter the new name.
3. The existing saved record is renamed; station/operator/layout data are unchanged.
4. Naming an existing scenario is rejected rather than overwriting its contents.

The UI preserves unsaved edits in the current canvas. Renaming the currently loaded
scenario updates the in-memory filename, so its next **Save Scenario** operation
continues to target the renamed save; the unsaved changes themselves are **not**
saved by the rename operation.

The endpoint is `POST /rename-scenario`, receiving JSON:

```json
{
  "filename": "OldLine.json",
  "new_name": "New Line",
  "expected_revision": "<revision from load>"
}
```

The response is `{ "status": "renamed", "filename": "New_Line.json", "revision": "..." }`.

Rename is available for both `CAPSTONE_STORAGE_BACKEND=json` and `sqlserver`.
No SQL schema changes or JSON migration are needed. For SQL Server, only the
`file_name` primary-key component of `dbo.CapstoneSaves` changes; `payload`,
`revision`, and timestamps remain unchanged. For JSON storage, original document
bytes are preserved. Collisions, missing saves and stale revisions produce clear
errors. Other module stores retain their original behavior.

## Verification commands

```powershell
python -m unittest discover -s tests -p "test_rename_storage.py" -v
python -m unittest discover -s tests -p "test_sqlserver_storage.py" -v
python tests/browser_rename_scenario.py
python tests/browser_builder_smoke.py
python tests/browser_new_line_direction.py
```

Browser tests require Playwright and Chromium. The SQL persistence contract
checks use SQLite as a lightweight stand-in. A live SQL Server instance and the
full Flask/SimPy test suite were not available in the packaging environment.
