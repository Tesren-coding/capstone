# ============================================================
# app.py
# Flask server — builder homepage, scenario simulation, events API
# ============================================================

import os
import json
import re
import hashlib
import tempfile
from threading import Lock

from flask import Flask, render_template, request, jsonify

from simulation import (
    run_scenario_simulation,
    ScenarioValidationError,
    ScenarioRuntimeError,
    normalize_scenario,
)

app = Flask(__name__)

SCENARIOS_DIR = "scenarios"
SCENARIO_SAVE_LOCK = Lock()


def scenario_revision(filepath):
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

# --------------------------------------------------------
# In-memory storage for the most recent simulation run.
# Stores events + takt_time + the scenario itself, so the
# animation page can derive positions/box types/operator
# rosters directly from the scenario — no hardcoded layout.
# --------------------------------------------------------
LAST_SIMULATION = {
    "events":    [],
    "takt_time": 30,
    "scenario":  None,
}


def safe_filename(name):
    """Convert a user-entered name into a safe filename."""
    name = name.strip()
    name = re.sub(r'[^A-Za-z0-9_\- ]', '', name)  # strip unsafe chars
    name = name.replace(" ", "_")
    return name or "untitled"


# --------------------------------------------------------
# Route: homepage — the scenario builder
# --------------------------------------------------------
@app.route("/")
def index():
    return render_template("builder.html")


# --------------------------------------------------------
# Route: run a builder-created scenario and store the result
# --------------------------------------------------------
@app.route("/launch", methods=["POST"])
def launch():
    global LAST_SIMULATION
    scenario = request.get_json()

    try:
        scenario = normalize_scenario(scenario)
        events, takt_time = run_scenario_simulation(scenario)
    except ScenarioValidationError as e:
        return jsonify({"status": "invalid", "errors": e.errors}), 400
    except ScenarioRuntimeError as e:
        return jsonify({"status": "runtime_error", "error": str(e)}), 400

    LAST_SIMULATION["events"]    = events
    LAST_SIMULATION["takt_time"] = takt_time
    LAST_SIMULATION["scenario"]  = scenario

    return jsonify({"status": "ok"})


# --------------------------------------------------------
# Route: return the last simulation's events + scenario
# --------------------------------------------------------
@app.route("/events")
def get_events():
    return jsonify(LAST_SIMULATION)


# --------------------------------------------------------
# Route: animation page
# --------------------------------------------------------
@app.route("/simulate")
def simulate():
    return render_template("simulate.html")


# --------------------------------------------------------
# Route: builder page (kept as its own path too, in case
# you want /builder to still work as an alias to homepage)
# --------------------------------------------------------
@app.route("/builder")
def builder():
    return render_template("builder.html")


# --------------------------------------------------------
# Scenario save / load / list / delete
# --------------------------------------------------------
@app.route("/save-scenario", methods=["POST"])
def save_scenario():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("scenario"), dict):
        return jsonify(status="invalid", error="Scenario data is required."), 400
    name = payload.get("filename") or payload.get("name", "untitled")
    if not isinstance(name, str):
        return jsonify(status="invalid", error="Scenario name must be text."), 400
    if name.endswith(".json"):
        name = name[:-5]
    stem = safe_filename(name)
    mode = payload.get("mode", "create")
    if mode not in ("create", "overwrite", "duplicate"):
        return jsonify(status="invalid", error="Unknown save mode."), 400

    with SCENARIO_SAVE_LOCK:
        os.makedirs(SCENARIOS_DIR, exist_ok=True)
        filename = stem + ".json"
        filepath = os.path.join(SCENARIOS_DIR, filename)
        if mode == "duplicate":
            # Repeated copies of Line_v2 continue as Line_v3, Line_v4, etc.
            root = re.sub(r"_v[0-9]+$", "", stem)
            version = 2
            while True:
                filename = f"{root}_v{version}.json"
                filepath = os.path.join(SCENARIOS_DIR, filename)
                try:
                    f = open(filepath, "x", encoding="utf-8")
                    break
                except FileExistsError:
                    version += 1
            try:
                with f:
                    json.dump(payload["scenario"], f, indent=2)
            except Exception:
                os.remove(filepath)
                raise
        elif mode == "create":
            try:
                f = open(filepath, "x", encoding="utf-8")
            except FileExistsError:
                return jsonify(status="exists", filename=filename), 409
            try:
                with f:
                    json.dump(payload["scenario"], f, indent=2)
            except Exception:
                os.remove(filepath)
                raise
        else:
            if not os.path.exists(filepath):
                return jsonify(status="missing", error="The original scenario no longer exists. Save a new version."), 409
            expected = payload.get("expected_revision")
            if expected and expected != scenario_revision(filepath):
                return jsonify(status="conflict", error="This scenario changed since you loaded it. Reload it or save a new version."), 409
            fd, temp_path = tempfile.mkstemp(dir=SCENARIOS_DIR, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(payload["scenario"], f, indent=2)
                os.replace(temp_path, filepath)
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        revision = scenario_revision(filepath)
    return jsonify(status="saved", filename=filename, revision=revision)


@app.route("/list-scenarios")
def list_scenarios():
    os.makedirs(SCENARIOS_DIR, exist_ok=True)
    files = [f for f in os.listdir(SCENARIOS_DIR) if f.endswith(".json")]
    files.sort()
    return jsonify({"files": files})


@app.route("/load-scenario/<filename>")
def load_scenario(filename):
    filename = safe_filename(filename.replace(".json", "")) + ".json"
    filepath = os.path.join(SCENARIOS_DIR, filename)

    if os.path.exists(filepath):
        with SCENARIO_SAVE_LOCK:
            with open(filepath, "rb") as f:
                raw = f.read()
            scenario_data = json.loads(raw)
            revision = hashlib.sha256(raw).hexdigest()
        return jsonify(found=True, scenario=scenario_data, filename=filename, revision=revision)

    return jsonify({"found": False, "scenario": None})


@app.route("/delete-scenario/<filename>", methods=["POST"])
def delete_scenario(filename):
    filename = safe_filename(filename.replace(".json", "")) + ".json"
    filepath = os.path.join(SCENARIOS_DIR, filename)

    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({"status": "deleted"})

    return jsonify({"status": "not_found"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
