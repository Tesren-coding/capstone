# Import JSON in hosted Line Builder

## What's changed

- The Line Builder **Scenario Files** section has an always-visible **Import JSON…** button.
- It lets each browser user choose an existing `.json` scenario from their own computer, including when the Flask application runs on a different machine and is opened through HTTP.
- The browser sends the JSON contents to the existing `/import-scenario` endpoint **only for validation and normalization**. This endpoint does not create a stored scenario in SQL Server or the server's JSON folder.
- Invalid JSON or an invalid scenario shows an error and leaves the current line unchanged. The user can cancel before replacing unsaved editor changes.
- When a user imports while Server storage is selected, the editor changes to **Download / Open File** to avoid unintentionally storing personal files on the server. Users can still explicitly select **Server** to save there later.
- Importing a file does not overwrite the original file on disk. After editing, **Save Scenario** downloads a new JSON file in download mode, or saves to a chosen device folder where the browser supports that feature.
- **Export JSON** continues to download a copy of the current line directly from the browser.
- All existing scenario schemas and local-folder saving behavior remain intact.

## Instructions

1. Open **Line Builder → Scenario Files**.
2. Click **Import JSON…** and select the JSON scenario file from your device.
3. Confirm replacement if the builder contains unsaved changes.
4. Edit the line and click **Save Scenario**. On a remote HTTP connection this downloads a file to the user's computer.
5. To load it again, choose **Import JSON…** and select that downloaded file.

**Note:** Direct *folder* access is separate from individual-file import. Folder access usually requires HTTPS (or localhost) and Chrome/Edge. Import JSON works without HTTPS because it uses a standard browser file picker.

## Checks

- `tests/browser_explicit_json_import.py`: explicit import on remote HTTP, no silent server write, malformed file rejection and cancel confirmation.
- `tests/browser_remote_http_device_files.py`: import and save download on remote HTTP.
- `tests/browser_local_folder_saves.py`: secure-context folder workflow remains available.

No database changes or new Python packages required.
