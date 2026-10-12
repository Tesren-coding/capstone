# ============================================================
# main.py
# Entry point — starts Flask server and opens browser
# ============================================================

import webbrowser
import threading
from app import app

def open_browser():
    webbrowser.open("http://localhost:5000/builder")

if __name__ == "__main__":
    # open browser after short delay to let Flask start
    timer = threading.Timer(1.0, open_browser)
    timer.start()
    app.run(debug=False)