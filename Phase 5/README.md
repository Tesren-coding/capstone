# NFPS Repair Line Simulation — Phase 5

## Overview
This project simulates the NFPS (Non-Flight Parts Screening) repair line
using SimPy for discrete event simulation and Pygame for visualization.
Phase 5 introduces a Flask-based web configuration page that allows the
user to adjust takt time, station cycle times, and view operator
sequences before launching the simulation.

## What's New in Phase 5
- Flask web server serving a configuration page
- User can edit takt time, incoming parts count, and station cycle times
  through the browser
- Launch button sends configuration to the backend and starts the
  Pygame simulation with the updated values
- Simulation runs in a separate thread so the browser remains responsive

## Folder Structure
Phase 5/ ├── app.py # Flask server — routes and launch logic ├── main.py # Entry point — starts Flask and opens browser ├── data.py # Default station, operator, and box data ├── simulation.py # SimPy simulation logic (accepts config) ├── visualization.py # Pygame main animation loop ├── layout.py # Station and box position calculations ├── drawing.py # Pygame drawing functions ├── state.py # Operator and part tracking state ├── templates/ │ ├── base.html # Shared page layout │ └── config.html # Configuration form and launch button ├── static/ │ └── style.css # Page styling └── images/ ├── part.png # Custom part image └── SWIP.png # SWIP box image

cd "Phase 5"
python main.py

Browser (config.html)
       │
       │  user submits settings
       ▼
Flask (app.py) ── /launch route
       │
       │  runs in background thread
       ▼
simulation.py ── SimPy generates event timeline
       │
       ▼
visualization.py ── Pygame renders the animation