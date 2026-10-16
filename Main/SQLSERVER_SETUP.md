# SQL Server Express setup — Capstone Line Planning Toolkit

This release adds SQL Server Express storage for all **four saved-document types**:

| Module | Legacy JSON directory | SQL save type |
| --- | --- | --- |
| Line Builder | `scenarios/` | `scenario` |
| PQPR | `pqpr_projects/` | `pqpr` |
| Line Balancing/Yamazumi | `balancing_plans/` | `balancing` |
| Builder Setup | `builder_setups/` | `builder_setup` |

All **Save**, **Load**, **List**, **Duplicate**, and available **Delete** operations use SQL when `CAPSTONE_STORAGE_BACKEND=sqlserver`. Existing front-end code, endpoint paths, filenames ending in `.json`, save revision checks, preview, generation and simulation continue unchanged. `.json` filenames in the interface are *logical names*, not files written by SQL mode. Explicit JSON **Import/Export** remains available for portable backups.

## 1. Install prerequisites (Windows)

1. Install **Microsoft SQL Server Express**. In the installer, note your server instance name (often `SQLEXPRESS`). Choose an authentication mode. Windows Authentication works well on a single Windows machine.
2. Install **SQL Server Management Studio (SSMS)** separately to administer the server.
3. Install **Microsoft ODBC Driver 18 for SQL Server** (64-bit for 64-bit Python).
4. In the application folder, run `python -m pip install -r requirements.txt`. This includes `pyodbc` along with Flask, SimPy and openpyxl.
5. Check you can connect in SSMS to `localhost\SQLEXPRESS` using **Windows Authentication**. Some installations use `.` or `(local)` instead, or a different instance name.

SQL Server Express is a **database server**. Your web users do *not* need SQL Server installed on their computers. Only the server running the database needs it; the Flask application needs the ODBC driver and network access to that server.

## 2. Create the database

Open `SQLSERVER_SETUP.sql` in SSMS and execute it while connected to the **SQL Server instance**. This creates `CapstoneLinePlanning` if it does not already exist. Use a login with database creation permission.

**SQL permissions:** The account running Flask must be allowed to connect to the database and have `SELECT`, `INSERT`, `UPDATE`, and `DELETE` permissions on `dbo.CapstoneSaves`. On its **first** use the application also needs `CREATE TABLE` permission (and permission to create in schema `dbo`), unless your DBA has already created the table. After initial setup, limit the application account to appropriate data access permissions. Do not expose SQL Server directly to the internet.

## 3. Enable SQL mode

**Simplest option on Windows:** edit the server name inside `start_sqlserver.bat` if necessary, then double-click it. It sets SQL mode and launches `python app.py`.

To run from PowerShell instead:

```powershell
$env:CAPSTONE_STORAGE_BACKEND = 'sqlserver'
$env:CAPSTONE_SQLSERVER_CONNECTION_STRING = 'Driver={ODBC Driver 18 for SQL Server};Server=localhost\SQLEXPRESS;Database=CapstoneLinePlanning;Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;'
python app.py
```

This uses Windows Authentication. The local development connection uses `TrustServerCertificate=yes` because many Express installations use a self-signed certificate. For a properly deployed server, use a trusted certificate, encryption and an appropriately restricted service identity. The database string may also be configured for SQL username/password authentication if required; keep credentials out of source control.

**If Python reports that `pyodbc` or the ODBC driver is missing:** Python package `pyodbc` and the *Microsoft ODBC Driver 18 for SQL Server* are **two separate installations**. Install both. To inspect installed drivers:

```powershell
python -c "import pyodbc; print(pyodbc.drivers())"
```

**If connection fails:** verify the instance name, Windows/SQL authentication, SQL Server service status, driver version, database existence, database access permissions, and (for connections from another machine) SQL Server TCP/IP/network/firewall configuration.

### Storage mode switch

| Setting | Behavior |
| --- | --- |
| `CAPSTONE_STORAGE_BACKEND=sqlserver` | Save/load in SQL Server Express (no JSON save files created). |
| `CAPSTONE_STORAGE_BACKEND=json` or not set | Existing local JSON-file storage (kept for compatibility and testing). |

SQL mode will **not silently fall back to local JSON** if SQL Server is offline: that would risk divergent data. Fix the connection instead.

## 4. Transfer existing JSON saves to SQL

**Before migration:** make a backup of your existing `scenarios/`, `pqpr_projects/`, `balancing_plans/`, and `builder_setups/` directories. These directories may be in your *previous* version of the application, not the new ZIP. The ZIP does not automatically include the saves from your computer. Copy your four saved-data folders into the updated project's root, **or** use `--data-root` to point at your existing project's root.

Set `CAPSTONE_SQLSERVER_CONNECTION_STRING` as shown in step 3, then run:

```powershell
python migrate_json_to_sqlserver.py --dry-run
python migrate_json_to_sqlserver.py
```

To migrate from an **older project folder** without copying files:

```powershell
python migrate_json_to_sqlserver.py --data-root 'C:\Users\YourUser\Documents\old-capstone-project'
```

Migration validates each JSON file, retains the original source files, preserves existing filenames and original revision hashes, and reports imported, identical, conflicting, and invalid documents. It does **not** overwrite existing SQL documents with different content. Re-running it safely skips identical imports.

If you consciously need to **replace** conflicting SQL documents with the old JSON files, first back up SQL, then run `python migrate_json_to_sqlserver.py --overwrite`. Never use this automatically.

**Important:** run the migration **before** editing migrated documents in SQL mode. Afterward, SQL is the active source of truth. If you later run the migration from an old JSON backup, the migration reports a conflict instead of losing newer SQL changes.

## 5. Verify the migration

In SSMS, connected to `CapstoneLinePlanning`, run:

```sql
SELECT save_type, COUNT(*) AS document_count
FROM dbo.CapstoneSaves
GROUP BY save_type;

SELECT save_type, file_name, revision, modified_utc
FROM dbo.CapstoneSaves
ORDER BY save_type, file_name;
```

Then open the toolkit and verify that a representative saved item appears and loads from **each** module. Test saving a new item, modifying and overwriting it, duplicating it, and reloading it after a restart. Keep your original JSON backup until you have checked the data.

## 6. Data design and future expansion

SQL table `dbo.CapstoneSaves` contains one row per saved document with `save_type`, `file_name`, `payload`, `revision`, and timestamps. `payload` is **JSON text stored inside SQL Server (`NVARCHAR(MAX)`)**, which is intentional: the existing tools use nested arrays and objects, and preserving the payload avoids breaking older save schemas and the existing browser editors. Your saves are persisted and managed in SQL Server; there is no server-side `.json` file being written in SQL mode.

For more advanced needs such as searching for all projects containing a particular framesize, cross-project analytics, advanced concurrency/multi-user permissions, or database relationships between PQPR and line balancing, a *second-stage relational schema* (projects, framesizes, processes, mappings, stations, operators, etc.) can be added later. This version changes **persistence**, not the domain-data model.

**Browser tab drafts:** The current editors still use browser `sessionStorage` for *unsaved drafts* and passing a plan between tools. This is separate from the **Save** function. Drafts are not automatically sent to SQL; choose **Save** to persist them.

**Multi-user security:** The current Flask API has no authentication or per-user authorization. SQL storage alone does not change that: if you make the web app available to other people, everyone with access to its save endpoints can see/modify the same saved documents. Add authentication, owners, roles and HTTPS before deploying to untrusted users.

## 7. Verification limitations

The code includes unit tests with an in-memory SQL Server protocol fake, but a real SQL Express integration test requires a running SQL Server Express instance and ODBC Driver 18 on Windows. Run the migration and test an actual save/load through the app on your machine to complete integration verification.
