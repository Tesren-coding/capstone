# Line Builder — Save Scenarios to a Folder on Your Device

## What this release adds

**Line Builder scenarios only** can now be saved directly to and reopened from a folder selected on the visitor's computer. This is a browser-side workflow; no arbitrary file paths are read or written by Flask.

Select one of three storage modes above the Line Builder canvas:

1. **Local Folder (your device)** — recommended. Choose a folder, save `.json` scenario files there, reopen them from the list, rename files or create numbered versions. The browser tries to remember the selected folder for this site on this device, but may ask you to reconnect and grant access in a later session.
2. **Server (existing saves)** — retains the original Flask JSON and SQL Server scenario save/load/rename endpoints. Select this mode to access existing server saves. This option does not move or delete server files.
3. **Download / Open File** — browser-only JSON download and import fallback; suitable if direct folder permissions are not supported or the site is opened over insecure HTTP.

The **Open Device File…** and **Export JSON** buttons remain accessible. The old Import JSON button has been replaced by the more descriptive file-opening action. Export JSON now uses the browser directly and does not POST the data to a server for a download.

## How to use Local Folder

1. Host the application with **HTTPS** for remote/LAN clients. For development on the same computer, `http://localhost:5000` or `http://127.0.0.1:5000` works as a secure context. Chrome / Edge are the recommended browsers.
2. Open **Line Builder**, choose **Local Folder (your device)** under Scenario storage, and click **Choose Folder…**.
3. Select an existing folder or create one, e.g., `Documents/Capstone/Scenarios`, and approve file access in your browser.
4. Click **Save Scenario**, enter a file name, and verify that it appears in the selected folder.
5. Later, select that file from the dropdown and click **Load Scenario**. Use **Refresh Files** if changes were made outside the app.
6. For an existing scenario saved on the server, choose **Server**, load the file, change to **Local Folder**, and click **Save Scenario**. This creates a local copy without deleting the server save.

## Safe storage behavior

- Local Folder stores regular standalone `.json` scenario files. It does **not** use SQL or save those files into the server's `scenarios/` directory.
- Saving over an existing file always requires a confirmation. **Save new version** creates a numbered file (`_v2`, `_v3`, etc.) instead of overwriting.
- If a loaded device file changed externally since it was opened, overwriting is blocked. You can reload the file or save a new version.
- Rename copies the complete original data, verifies the new copy, then removes the original filename. If it fails before removal, the original remains.
- Files are not auto-deleted, and switching storage modes never moves or erases files.
- Browser permissions and the remembered folder handle are scoped to the browser profile and website origin. A different device, browser profile, or website hostname may need its own folder selection.
- Any unsaved browser draft still uses existing sessionStorage recovery; that is not a reliable long-term backup.
- The app still sends scenario data to Flask when running simulations or opening JSON files for schema normalization; these validation calls do not persist a scenario on the server. **Local saving only changes persistence**; it does not make the simulation run entirely offline.

## Compatibility and limits

- Direct device folder access requires the File System Access API in a secure context, typically **desktop Chrome or Edge + HTTPS** (or `localhost`). Accessing a LAN server by plain `http://192.168.x.x` often does not qualify; set up HTTPS or use Download / Open File.
- Folder access is permission-based. Browsers may revoke permission or ask for a new confirmation in future visits; click **Choose Folder…** to reconnect.
- Browser-managed folder handles are remembered in IndexedDB if permitted. Scenario contents are not saved in IndexedDB, just the folder handle. Scenario JSON remains in the folder chosen by the user.
- This changes **Line Builder scenario** storage only. PQPR, Line Balancing, and Builder Setup still use their existing storage systems. A single `.capstone` project file spanning all modules is a separate future enhancement.
- There is no automatic sync across devices, history restoration, or backup of local device files. Use a backed-up folder (for example, an organization-approved synced folder), and keep additional backups of important layouts.

## Files changed

- `templates/builder.html` — storage selector and folder controls.
- `static/js/local-folder-store.js` — browser directory permissions, file listing, save/load/version/rename, saved handle in IndexedDB.
- `static/js/builder.js` — store selector integration, safe save/load, conflict detection, client-side JSON export and session draft compatibility.
- `tests/browser_local_folder_saves.py` — browser exercise of local folder save/load/rename/switch/fallback with mocked File System Access API.
- `tests/browser_builder_smoke.py` — loads the additional module in existing browser tests.
- `Updates/HOSTED_SERVER_DEVICE_FILE_ACCESS.md` — deployment fallback for insecure HTTP.

No SQL migration or backend storage change is necessary.
