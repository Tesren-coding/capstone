# ============================================================
# app.py
# Flask server — config page, simulation launch, and events API
# ============================================================

from flask import Flask, render_template, request, jsonify
import data as default_data

app = Flask(__name__)

# --------------------------------------------------------
# In-memory storage for the most recent simulation run
# In a real production app this would be a database or
# session, but for this capstone a global variable is fine
# since only one simulation runs at a time.
# --------------------------------------------------------
LAST_SIMULATION = {
    "events":    [],
    "takt_time": default_data.TAKT_TIME,
}

# --------------------------------------------------------
# Route: config page
# --------------------------------------------------------
@app.route("/")
def index():
    return render_template("config.html",
                           stations   = default_data.STATIONS,
                           operators  = default_data.OP_SEQUENCES,
                           takt_time  = default_data.TAKT_TIME,
                           incoming   = default_data.SPECIAL_BOXES["Incoming"]["start"])

# --------------------------------------------------------
# Route: run simulation and store result
# --------------------------------------------------------
@app.route("/launch", methods=["POST"])
def launch():
    global LAST_SIMULATION

    config = request.get_json()

    from simulation import run_simulation
    events, takt_time = run_simulation(config)

    # store result for the /events endpoint to serve
    LAST_SIMULATION["events"]    = events
    LAST_SIMULATION["takt_time"] = takt_time

    return jsonify({"status": "ok"})

# --------------------------------------------------------
# Route: return the last simulation's events as JSON
# --------------------------------------------------------
@app.route("/events")
def get_events():
    return jsonify(LAST_SIMULATION)

# --------------------------------------------------------
# Route: return station, box, and operator data as JSON
# This lets JavaScript know the layout without duplicating
# the data.py values by hand in JS.
# --------------------------------------------------------
@app.route("/layout-data")
def get_layout_data():
    return jsonify({
        "stations":      default_data.STATIONS,
        "special_boxes": default_data.SPECIAL_BOXES,
        "operators":     default_data.OPERATORS,
        "op_start_part": default_data.OP_START_PART,
        "dimensions": {
            "window_width":   default_data.WINDOW_WIDTH,
            "window_height":  default_data.WINDOW_HEIGHT,
            "station_width":  default_data.STATION_WIDTH,
            "station_height": default_data.STATION_HEIGHT,
            "bottom_row_y":   default_data.BOTTOM_ROW_Y,
            "top_row_y":      default_data.TOP_ROW_Y,
            "row_start_x":    default_data.ROW_START_X,
            "row_gap":        default_data.ROW_GAP,
            "box_width":      default_data.BOX_WIDTH,
            "box_height":     default_data.BOX_HEIGHT,
        }
    })

# --------------------------------------------------------
# Route: animation page
# --------------------------------------------------------
@app.route("/simulate")
def simulate():
    return render_template("simulate.html")

# --------------------------------------------------------
# Entry point
# --------------------------------------------------------
import json
import os
import re

LAYOUTS_DIR = "layouts"

def safe_filename(name):
    """Convert a user-entered name into a safe filename."""
    name = name.strip()
    name = re.sub(r'[^A-Za-z0-9_\- ]', '', name)  # strip unsafe chars
    name = name.replace(" ", "_")
    return name or "untitled"

# --------------------------------------------------------
# Route: save a named layout to disk
# --------------------------------------------------------
@app.route("/save-layout", methods=["POST"])
def save_layout():
    payload      = request.get_json()
    layout_name  = payload.get("name", "untitled")
    layout_data  = payload.get("layout", {})

    filename = safe_filename(layout_name) + ".json"
    os.makedirs(LAYOUTS_DIR, exist_ok=True)

    filepath = os.path.join(LAYOUTS_DIR, filename)
    with open(filepath, "w") as f:
        json.dump(layout_data, f, indent=2)

    return jsonify({"status": "saved", "filename": filename})

# --------------------------------------------------------
# Route: list all saved layout files
# --------------------------------------------------------
@app.route("/list-layouts")
def list_layouts():
    os.makedirs(LAYOUTS_DIR, exist_ok=True)
    files = [f for f in os.listdir(LAYOUTS_DIR) if f.endswith(".json")]
    files.sort()
    return jsonify({"files": files})

# --------------------------------------------------------
# Route: load a specific layout file by name
# --------------------------------------------------------
@app.route("/load-layout")
@app.route("/load-layout/<filename>")
def load_layout(filename=None):
    if filename is None:
        # No specific file requested — return "not found" gracefully,
        # or point this at a default/last-used layout if you have one
        return jsonify({"found": False, "layout": None})

    filename = safe_filename(filename.replace(".json", "")) + ".json"
    filepath = os.path.join(LAYOUTS_DIR, filename)

    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            layout_data = json.load(f)
        return jsonify({"found": True, "layout": layout_data, "filename": filename})

    return jsonify({"found": False, "layout": None})

# --------------------------------------------------------
# Route: delete a saved layout file
# --------------------------------------------------------
@app.route("/delete-layout/<filename>", methods=["POST"])
def delete_layout(filename):
    filename = safe_filename(filename.replace(".json", "")) + ".json"
    filepath = os.path.join(LAYOUTS_DIR, filename)

    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({"status": "deleted"})

    return jsonify({"status": "not_found"})

if __name__ == "__main__":
    app.run(debug=True)