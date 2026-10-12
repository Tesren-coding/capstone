# Phase 1 (proof-of-concept)
## Objective
The objective of Phase 1 is to validate the concept using two open-source libraries: Pygame and SimPy.

## Discrete-Event Simulation
This project is built around a discrete-event simulation, where SimPy and Pygame work together — SimPy handles the underlying logic and timing, while Pygame provides a visual representation of the simulated process.

### Pygame
Pygame is used to visualize the simulation and acts as the frontend platform for the project. It was chosen for its simplicity, making it easy to implement and validate the concept quickly. As the project progresses to later phases, Pygame will likely be phased out in favor of a more visually polished frontend. For now, it remains a viable solution for a simple proof of concept.

### SimPy
SimPy is used to simulate the sequence of events, taking into account the cycle time and takt time of the operation. It functions as the logic controller of the program, scheduling and sequencing events to ensure the simulation runs accurately and consistently over time.

## How It Comes Together
The key operational data is hardcoded into simulation.py, which uses SimPy to organize event timing and sequencing. Animation is handled separately in visualization.py, which uses Pygame to render the simulation. visualization.py draws timing data from simulation.py to determine when specific animations should occur.

# Phase 2 (Application of proof-of-concept)
## Objective
Phase 2 objective is to bring the proof-of-concept in Phase 1 to a real working operation such as the NFPS line standard work flow. This is to validate if the concept still works with multiple moving pieces such as in real working context. 

## Improvement to structure
The program structure is now split into: simulation, visualization and data. The split is to facilitate the increase in data. Keeping it in a separate file allows us to easily organize and draw information from to the other program files. 

# Phase 3 (Inclusion of SWIP box and part png)

# Phase 4 (Frontend interaction)

# Phase 5 (Movement to web-based platform)
## Objective
Phase 5 introduces a Flask-based web configuration page that allows the user to adjust takt time, station cycle times, and view operator on a web-browser. The animation still uses pygame.

## What's New in Phase 5
- Flask web server serving a configuration page
- User can edit takt time, incoming parts count, and station cycle times
  through the browser
- Launch button sends configuration to the backend and starts the
  Pygame simulation with the updated values
- Simulation runs in a separate thread so the browser remains responsive

## Folder Structure
Phase 5  
├── app.py # Flask server — routes and launch logic  
├── main.py # Entry point — starts Flask and opens browser  
├── data.py # Default station, operator, and box data  
├── simulation.py # SimPy simulation logic (accepts config)   
├── visualization.py # Pygame main animation loop  
├── layout.py # Station and box position calculations   
├── drawing.py # Pygame drawing functions  
├── state.py # Operator and part tracking state  
├── templates/  
│ ├── base.html # Shared page layout  
│ └── config.html # Configuration form and launch button  
├── static/  
│ └── style.css # Page styling  
└── images/  
  ├── part.png # Custom part image  
  └── SWIP.png # SWIP box image  

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

# Phase 6 (Animation moved to web-based)
## Objective

The objective of Phase 6 is to achiveve feature parity between the original Pygame application to the new web-based version. Because it uses two seperate technology, the movement was big but successful

---
## Overview

Phase 6 replaces the Pygame desktop visualization (Phases 1-5) with a
fully browser-based animation. The simulation now runs as a web
application — anyone on the network can open a link in their browser
and watch the repair line animate, with no Python or Pygame
installation required on their end.

The backend simulation logic (SimPy) is unchanged. Only the
**visualization layer** was rebuilt, moving from Pygame (Python) to
HTML5 Canvas (JavaScript).

> **Feature parity achieved:** the web version supports everything the
> Pygame version did — station rendering, operator movement, part
> pickup/drop, live counters, Start/Stop controls, and the progress
> banner — just running in a browser instead of a desktop window.

---

## Architecture
| Flow Stage | Who | Action |
| ----------- | ----------- | ----------- |
| 1. Trigger | Browser | User clicks "Launch", sending settings to Flask. |
| 2. Logic | SimPy | 	Python calculates the entire timeline of events (the math) |
| 3. Transfer | Flask | 	Sends that timeline to the browser as a JSON file |
| 4. Visuals | 	Browser | JavaScript reads the JSON and renders it on a Canvas |


1. **SimPy** (`simulation.py`) runs the discrete event simulation and
   produces a list of timestamped events (pickup, drop, work, idle) —
   completely unchanged from earlier phases.
2. **Flask** (`app.py`) serves the web pages and exposes the
   simulation data as JSON through a few API routes.
3. **Browser** (HTML + JavaScript) fetches that JSON data and draws
   the entire animation on an HTML5 `<canvas>` element, frame by
   frame, using `requestAnimationFrame`.

---

## Folder Structure
Phase 6/  
├── app.py # Flask server — routes and API  
├── main.py # Entry point — starts Flask, opens browser   
├── data.py # Station/operator/box definitions (unchanged)  
├── simulation.py # SimPy simulation logic (unchanged)  
├── templates/  
│ ├── base.html # Shared page layout (header/footer)  
│ ├── config.html # Configuration form page  
│ └── simulate.html # Animation page — canvas + JS logic  
├── static/  
│ ├── style.css # Page styling  
│ ├── js/  
│ │ ├── layout.js # Station/box position calculations  
│ │ ├── draw.js # Canvas drawing functions  
│ │ └── state.js # Operator/part state tracking  
│ └── images/  
│ ├── part.png # Custom part image  
│ └── SWIP.png # SWIP box image  
└── README.md  


---

## Backend — app.py

Flask exposes four routes:

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Renders the configuration page (`config.html`) |
| `/launch` | POST | Runs `simulation.py` with the submitted config, stores the result |
| `/events` | GET | Returns the last simulation's events + takt time as JSON |
| `/layout-data` | GET | Returns station/box/operator definitions + canvas dimensions as JSON |
| `/simulate` | GET | Renders the animation page (`simulate.html`) |

### Why JSON APIs instead of embedding data directly in HTML?

Keeping `data.py` as the single source of truth means any change to
station names, cycle times, or operator colors automatically appears
in the browser without editing any JavaScript or HTML — the frontend
simply asks Flask for the current data every time the page loads.

### In-memory storage

```python
LAST_SIMULATION = {
    "events":    [],
    "takt_time": default_data.TAKT_TIME,
}
```
## Frontend — Templates
**base.html**  
The shared page shell — header, footer, and CSS link. Both config.html and simulate.html extend this using Jinja's {% extends %} / {% block content %} system, so the header/footer never need to be repeated.

**config.html**  
The landing page. Displays:

Takt time and incoming parts count (editable)
Every station with its editable cycle time
Every operator's step sequence (read-only, for reference)
A Launch Simulation button
When clicked, JavaScript collects all the input values into a JSON object and sends it via fetch() to /launch. On success, the browser redirects to /simulate.

**simulate.html**  
The animation page. This is where most of the JavaScript logic lives (described in detail below). It contains:

A status text area (shows loading progress)
The `<canvas id="sim-canvas">` element where everything is drawn  
Start/Stop buttons (created dynamically via JavaScript)  
All the animation logic in an inline `<script>` block  

## JavaScript Files
### draw.js — Canvas Drawing Functions
This is the JavaScript equivalent of the old drawing.py. It knows how to draw each visual element — it does not know anything about timing, movement, or simulation logic.

| Function	| Draws |
| ---------| -------- |
| drawStation( )	| A station rectangle, its name, ID, cycle time. Highlights with a colored tint + yellow border when active |
| drawBox( )	| A special box (Incoming, HT, Coating, SWIP, Packing). Uses an image if available, otherwise a plain box with a dotted border |
| drawPart( ) |	The part image (falls back to a hatched circle if the image fails to load) |
| drawPartPlaceholder( )	| The fallback hatched circle used if part.png isn't available |
| drawOperator( ) | 	A colored circle with the operator's name in the center |
| drawBanner( ) |	The dark blue header bar with the cycle time text and progress bar |
| drawLegend( ) |	The row of operator color dots + part icon at the bottom of the canvas |

**Color handling** — toRgbString() / toRgbaString()
Station and operator colors come from data.py as Python tuples, e.g. (220, 50, 50). When Flask converts this to JSON, it becomes a plain array: [220, 50, 50]. HTML | Canvas cannot use an array directly as a fill color — it needs a string like "rgb(220,50,50)".

```javascript
function toRgbString(colorArray) {
    if (Array.isArray(colorArray)) {
        return `rgb(${colorArray[0]}, ${colorArray[1]}, ${colorArray[2]})`;
    }
    return colorArray;
}

function toRgbaString(colorArray, alpha = 1) {
    if (Array.isArray(colorArray)) {
        return `rgba(${colorArray[0]}, ${colorArray[1]}, ${colorArray[2]}, ${alpha})`;
    }
    return colorArray;
}

```
- toRgbString() is used for solid colors (operator circles, legend dots).
- toRgbaString() is used for the active station highlight, with a low alpha (0.35) so the station's text remains readable while still showing which operator's color is working there.

---

### state.js — Operator & Part State Tracking
This is the JavaScript equivalent of the old state.py. It builds and holds all the "live" data that changes every frame — positions, whether an operator is carrying a part, which parts are sitting where, and the Incoming/Packing counters.

```javascript
function buildOperatorState(events, stationCenters, boxCenters, opNames,
                             opStartPart, incomingStart, packingStart) {
    ...
    return {
        opEvents,          // each operator's full event list
        opPositions,        // current x,y of each operator
        opTargets,          // where each operator is currently walking to
        opEventIndex,       // which event index each operator is on
        opCycleLength,      // how many events make up one full cycle (for looping)
        opHasPart,          // true/false — is this operator carrying a part
        opDropoffTarget,    // coordinates operator must reach before dropping
        opPendingDropoff,   // the event waiting to be completed once operator arrives
        partPositions,      // where to draw the carried part (offset near operator)
        droppedParts,       // parts currently sitting at a station/box, waiting for pickup
        counters,           // { incoming: N, packing: N }
        getLocCenter,       // helper: converts a station id or box key into {x, y}
    };
}
getLocCenter(loc)
```
Events reference locations either as a **number** (station ID, e.g. 4) or a **string** (box key, e.g. "SWIP_1"). This function checks the type and looks up the correct center coordinate from either stationCenters or boxCenters.


#### Why _opCycleLength_ matters
The simulation produces one long list of events covering 100 takt cycles. Rather than storing 100 repeated copies of the same route, the animation simply **loops back** to the start of an operator's event list once it reaches the end within a cycle. opCycleLength tracks exactly how many events make up one loop, calculated by counting events until the first "idle" status is hit.

# Phase 7 (Start line designer process - allowing user to move station)

## Objective
The objective is to allow the user to create a line from scratch. Moving from Phase 6 to Phase 7, we can validate the line creation process by leaving a working standard work operation and allowing the user to replace and move stations as they please.

## Validation
1. The phase is successful if the stations can be dragged and dropped to any location. 
2. The layout can be saved
3. Stations can be deleted and add

## changes
- SWIP box updated
- added drag and drop option
- save and load layout 

## Bugs and problems
As of this phase, the added stations does not have any identity meaning it is not part of the working line. The simulation would also stop when you delete any of the working station and reproduce it again by resetting. 

# Phase 8 (Bug fixes and changes to saving feature)

# Phase 9 (Builder program)
## Objective
Compared to the previous few phases, phase 9 will take a step towards the builder function. Instead of having the stations, boxes and operators hardcoded, the user will be able to build the line and decide how it will be run.

## Validation
With free building comes also a need to validate the simulation. Some rules governing the simulation would be:
1. Operator cannot start 'work' at a station without parts
2. Operator cannot 'pick' if there are no parts at the station/box
3. Operator cannot 'drop' parts if there exist another part at the station/box unless:  
a. it is a OUT box  
b. it is a packing box  

## Overview
With the changes to a builder UI, there would be a new html required: `builder.html`  
This would be the new platform that user can use to craft their desire line operation. A new simulation file is also require to run custom scenarios as the previous simulation engine ran on hardcoded data in `data.py`

# Phase 12
## Factory Line Simulation Tool

A scenario-driven factory line simulator: build a line visually, run a
discrete-event simulation of it, and watch the result animate on a canvas.

## Components

- **`builder.html`** — visual editor. Place stations, operators (with
  pick/work/drop sequences), and IN/OUT/SWIP boxes on a canvas. Save/load
  scenarios as JSON (persisted under `/scenarios`).
- **`simulation.py`** — SimPy-based discrete event engine. Validates a
  scenario, then runs it, producing a timestamped event log.
- **`simulate.html`** — playback page. Fetches the event log and animates
  operators walking, picking up/dropping parts, and updates box counters
  and a takt-time clock live.

## Architecture
builder.html → POST /save-scenario → /scenarios/*.json builder.html → POST /launch → simulation.py (validate + run) simulate.html → GET /events → { scenario, events, takt_time }


Everything is scenario-driven — there is no hardcoded layout or fixed
station/operator data. All positions, sequences, and box behavior come
from the JSON scenario built in `builder.html`.

## Key files

| File | Role |
|---|---|
| `app.py` | Flask routes: `/`, `/builder`, `/launch`, `/events`, `/save-scenario`, `/load-scenario/<file>`, `/list-scenarios` |
| `simulation.py` | Scenario validation + SimPy engine |
| `static/js/draw.js` | Canvas primitives: `drawStation`, `drawBox`, `drawOperator`, `drawPart`, `drawBanner`, `drawLegend` |
| `static/js/positions.js` | Derives station/box rects + center points from scenario `x/y/w/h` |
| `static/js/state.js` | Builds and advances operator/box animation state each frame |
| `templates/builder.html` | Scenario editor (own inline canvas drawing, separate from `draw.js`) |
| `templates/simulate.html` | Playback page — animation loop, canvas rendering |
| `templates/base.html` | Shared layout/header |

## Scenario JSON shape

```json
{
  "takt_time": 30,
  "stations": {
    "1": { "x": 681, "y": 360, "w": 120, "h": 70, "name": "...", "cycle_time": 10, "has_part": false }
  },
  "operators": {
    "Op1": {
      "x": 748, "y": 311, "name": "Op1", "color": [220, 60, 60],
      "sequence": [
        { "action": "pick", "loc": "IN_1" },
        { "action": "drop", "loc": "1" },
        { "action": "work", "loc": "1" },
        { "action": "pick", "loc": "1" },
        { "action": "drop", "loc": "OUT_2" }
      ]
    }
  },
  "boxes": {
    "IN_1":  { "x": 551, "y": 365, "w": 90, "h": 60, "type": "in",   "name": "IN_1",  "start_count": 10 },
    "OUT_2": { "x": 843, "y": 365, "w": 90, "h": 60, "type": "out",  "name": "OUT_2", "capacity": 50 }
  }
}