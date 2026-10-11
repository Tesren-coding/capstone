# ============================================================
# app.py
# Flask server — builder homepage, scenario simulation, events API
# ============================================================

import os
import json
import re

from flask import Flask, render_template, request, jsonify

from simulation import (
    run_scenario_simulation,
    ScenarioValidationError,
    ScenarioRuntimeError,
)

app = Flask(__name__)

SCENARIOS_DIR = "scenarios"

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
    payload       = request.get_json()
    scenario_name = payload.get("name", "untitled")
    scenario_data = payload.get("scenario", {})

    filename = safe_filename(scenario_name) + ".json"
    os.makedirs(SCENARIOS_DIR, exist_ok=True)

    filepath = os.path.join(SCENARIOS_DIR, filename)
    with open(filepath, "w") as f:
        json.dump(scenario_data, f, indent=2)

    return jsonify({"status": "saved", "filename": filename})


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
        with open(filepath, "r") as f:
            scenario_data = json.load(f)
        return jsonify({"found": True, "scenario": scenario_data})

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