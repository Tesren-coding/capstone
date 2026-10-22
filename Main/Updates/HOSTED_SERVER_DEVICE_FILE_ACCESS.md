# Hosted server: loading scenarios from each user's device

## Problem

When Line Builder runs on a separate server (particularly at a LAN IP URL like
`http://192.168.x.x:5000`), the Flask server cannot access each browser user's
local folders. The File System Access API (`showDirectoryPicker`) also requires
a secure context and compatible browser, typically desktop Chrome or Edge on
HTTPS or localhost. A previous interface hid the JSON import control, so users
on ordinary remote HTTP had no obvious way to reopen their device files.

## Fix

- **Open Device File…** is now always shown in Scenario Files. It launches the
  standard browser file chooser and opens a `.json` scenario, even on HTTP.
- The chosen JSON file is read by the browser. The scenario is submitted to
  Flask's existing `/import-scenario` endpoint for schema validation, but **is
  not persisted** to the server's JSON/SQL scenario store.
- If a user previously selected Local Folder but the current website does not
  support direct folder access, the default storage choice becomes
  **Download / Open File**, not the server. Saving in this mode downloads a new
  JSON file to the client device. The server only gets scenario data when
  needed for normalization or simulation.
- The storage panel clearly says when HTTPS is needed for folder access.
- **Server (existing saves)** remains an explicit optional choice so earlier
  server saves are still accessible. No files are deleted or migrated.
- On supported HTTPS origins, the original **Local Folder** workflow is
  unchanged: Choose Folder, Save directly into that folder, Refresh Files,
  Load, rename, and create versions.

## For users on a server-hosted HTTP page

1. Open Line Builder in Chrome or Edge.
2. Under Scenario storage, select **Download / Open File** (it is automatically
   selected if direct folder access is unavailable and Local Folder was preferred).
3. Click **Open Device File…** and choose a `.json` file from the user's own PC.
4. Edit the line; click **Save Scenario** to download an updated JSON file.
5. Keep the downloaded file in a backed-up folder. To continue later, open it
   again using **Open Device File…**.

Saving via the downloaded-file fallback cannot silently overwrite the original
file: browsers generally save to Downloads or prompt the user for a location,
depending on settings. Rename or replace old versions manually if needed.

## For true choose-once, save-back-to-folder behavior

Deploy the application behind **HTTPS using a trusted certificate** and access
it via that HTTPS URL in a supported desktop browser. Then choose
**Local Folder (your device)** and grant permission. `localhost` is an
exception *only for the user who is opening a browser on their own machine*;
opening `http://localhost:5000` from another user's machine points to that
other machine, not your Flask server.

Folder permissions are scoped to the browser profile and exact website origin.
If the app moves from localhost to a server hostname, users may need to
select and authorize their folders again. The files themselves remain on their
computers, unchanged.

## Verification

- `tests/browser_remote_http_device_files.py`: simulated HTTP browser opens
  device JSON, saves by download, and performs no implicit server save.
- `tests/browser_local_folder_saves.py`: HTTPS-capable mocked folder remains
  functional (save, load, rename, versions, overwrite checks).
- All 8 JavaScript and 24 Builder/browser regression scripts passed (including
  the two tests above). Flask/SQL production deployment was not tested.

## Files changed

- `templates/builder.html` — visible **Open Device File…** button.
- `static/js/builder.js` — HTTP-safe fallback, labels, file open handler.
- `tests/browser_builder_smoke.py` — existing server-mode smoke tests explicitly
  select Server, rather than relying on the old insecure-context default.
- `tests/browser_local_folder_saves.py` — keeps Local Folder selected in a
  simulated secure browser.
- `tests/browser_remote_http_device_files.py` — regression coverage for HTTP.
- `tests/browser_line_tool_docking.py` and `tests/browser_player_grouped_tools.py`
  — updated expectations for visible local file opener.

No new dependencies, database changes, or scenario-format migration are needed.
