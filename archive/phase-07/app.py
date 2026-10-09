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

LAYOUT_FILE = os.path.join("layouts", "saved_layout.json")

# --------------------------------------------------------
# Route: save the current station/box positions to disk
# --------------------------------------------------------
@app.route("/save-layout", methods=["POST"])
def save_layout():
    layout_data = request.get_json()

    os.makedirs("layouts", exist_ok=True)
    with open(LAYOUT_FILE, "w") as f:
        json.dump(layout_data, f, indent=2)

    return jsonify({"status": "saved"})

# --------------------------------------------------------
# Route: load the saved layout, if one exists
# --------------------------------------------------------
@app.route("/load-layout")
def load_layout():
    if os.path.exists(LAYOUT_FILE):
        with open(LAYOUT_FILE, "r") as f:
            layout_data = json.load(f)
        return jsonify({"found": True, "layout": layout_data})

    return jsonify({"found": False, "layout": None})

# --------------------------------------------------------
# Route: delete the saved layout (reset to default)
# --------------------------------------------------------
@app.route("/reset-layout", methods=["POST"])
def reset_layout():
    if os.path.exists(LAYOUT_FILE):
        os.remove(LAYOUT_FILE)
    return jsonify({"status": "reset"})

if __name__ == "__main__":
    app.run(debug=True)