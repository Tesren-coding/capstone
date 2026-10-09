# ============================================================
# app.py
# Flask server — handles config page and simulation launch
# ============================================================

from flask import Flask, render_template, request, jsonify
import threading
import data as default_data

app = Flask(__name__)

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
# Route: launch simulation
# --------------------------------------------------------
@app.route("/launch", methods=["POST"])
def launch():
    config = request.get_json()

    # run simulation and visualization in a separate thread
    # so Flask can still respond to the browser
    def run():
        from simulation    import run_simulation
        from visualization import run_visualization
        events, takt_time = run_simulation(config)
        run_visualization(events, takt_time)

    thread = threading.Thread(target=run)
    thread.daemon = True
    thread.start()

    return jsonify({"status": "launched"})

# --------------------------------------------------------
# Entry point
# --------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=False)