# Requirements and setup

This guide explains how to run the Capstone Line Building Simulator on your own PC.
The application uses Python, Flask and SimPy, with a browser interface.

## 1. Requirements

| Requirement | Details |
| --- | --- |
| Computer | A desktop or laptop running Windows, macOS or Linux. |
| Python | Python 3.12 is the recommended setup version. Install it from [python.org](https://www.python.org/downloads/). |
| Python tools | `pip` and `venv`, normally included with Python. |
| Browser | A modern browser with JavaScript enabled, such as Chrome, Edge or Firefox. |
| Internet | Needed to download Python and install dependencies during initial setup. |
| Project folder | The complete extracted project, in a folder where you can save files. |

Required third-party Python packages are defined in `requirements.txt`:

```text
Flask>=3.1,<4
simpy>=4.1,<5
```

Flask runs the web application; SimPy runs the production-line simulation.
Installing from `requirements.txt` also installs their dependent packages.

**`requirements.md` is this guide. `requirements.txt` is the package list used by pip.**

## 2. Get the complete project

Extract the project ZIP before running it. Keep these files and folders together:

| Location | Contents |
| --- | --- |
| Project root | `app.py`, `simulation.py`, `scenario_schema.py`, `scenario_store.py`, `requirements.txt`; `main.py` is an optional launcher. |
| `templates/` | `base.html`, `builder.html`, `simulate.html`. |
| `static/` | `style.css`. |
| `static/js/` | `builder.js`, `playback.js`, `api.js`, `canvas-tools.js`, `draw.js`, `positions.js`, `state.js`. |
| `static/images/` | `Part.png`, `SWIP.png`; keep the exact filenames and capitalisation. |
| `scenarios/` | Saved scenario JSON files. The app creates this folder when needed. |

When transferring the project to another PC, copy your `scenarios/` folder if
you want to keep your saved layouts. Create a fresh virtual environment on each PC.

## 3. First-time setup on Windows

Install Python, then open **PowerShell** in the folder containing `app.py`.
For example, replace the path below with your actual project folder:

```powershell
cd "C:\path\to\capstone-qol-update"
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

If Windows does not recognise `python`, try `py --version`. If that works,
use `py -m venv .venv` to create the environment, then use the same
`.\.venv\Scripts\python.exe` commands above.

The `.venv` folder keeps this project's installed packages together. These
commands use its Python directly, so you do not need to activate it first.

## 4. Open and use the application

Once the server starts, open **http://localhost:5000** in your browser.
You should see the Scenario Builder. Keep the terminal open while using the app.

Create or load a scenario, configure its stations and operators, then select
**Run Simulation**. Save layouts with **Save Scenario**. Use **Import JSON**
to open a scenario file from your PC and **Export JSON** to download a portable
copy. Older supported formats are converted without changing the original file.
See `DATA_FORMAT.md` for compatibility rules.

Press **Ctrl+C** in the terminal to stop the server.

## 5. Start the application next time

Open PowerShell in the same project folder and run:

```powershell
.\.venv\Scripts\python.exe app.py
```

Then open **http://localhost:5000**. You only need to install packages again
if the dependency list changes or you recreate the environment.

To open the browser automatically, you can use the supplied launcher instead:

```powershell
.\.venv\Scripts\python.exe main.py
```

Run one launcher at a time.

## 6. macOS or Linux setup

Open Terminal in the folder containing `app.py` and run:

```bash
python3 --version
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python app.py
```

Open **http://localhost:5000**. For later runs, use just
`./.venv/bin/python app.py` from the project folder. Stop with **Ctrl+C**.
If your Linux installation lacks `venv` or `pip`, install the corresponding
Python packages through your distribution's package manager.

## 7. Troubleshooting

| Problem | What to check |
| --- | --- |
| `python` or `py` is not recognised | Check that Python is installed, reopen the terminal, and check its PATH configuration. |
| `No module named flask` or `simpy` | Run the dependency-install command using the same `.venv` Python used to start the app. |
| `requirements.txt` or `app.py` cannot be found | Open the terminal in the extracted folder containing those files. |
| Port 5000 is already in use | Stop the other copy of the app with Ctrl+C, then start it again. |
| Browser cannot connect | Check the terminal for errors and confirm the server is still running. Use `localhost:5000`, not a file opened directly in the browser. |
| Missing styles, images or templates | Check that the complete `static/` and `templates/` folders were copied and filenames match. |
| Old interface after updating files | Restart the app and refresh the browser with Ctrl+F5 on Windows. |
| Scenario cannot be saved | Check that the project folder and `scenarios/` folder are writable. |

## References

- [Python virtual environments](https://docs.python.org/3.12/library/venv.html)
- [Flask installation](https://flask.palletsprojects.com/en/stable/installation/)
