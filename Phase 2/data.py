# ============================================================
# data.py
# Central data bank for the NFPS Repair Line Simulation
# ============================================================

TAKT_TIME = 36

STATIONS = {
    1:  {"name": "Insp. Incoming Masking",  "cycle_time": 2,  "row": "bottom"},
    2:  {"name": "Incoming Blasting AO24",  "cycle_time": 17, "row": "bottom"},
    3:  {"name": "Cosmetic Blasting AO220", "cycle_time": 15, "row": "bottom"},
    4:  {"name": "Incoming FPI",            "cycle_time": 18, "row": "bottom"},
    5:  {"name": "Incoming Inspection",     "cycle_time": 15, "row": "bottom"},
    6:  {"name": "T800 Machining",          "cycle_time": 14, "row": "bottom"},
    7:  {"name": "Blending Defect",         "cycle_time": 18, "row": "bottom"},
    8:  {"name": "Swab Etch",               "cycle_time": 6,  "row": "bottom"},
    9:  {"name": "Local FPI",               "cycle_time": 11, "row": "bottom"},
    10: {"name": "Shotpeen",                "cycle_time": 6,  "row": "top"},
    11: {"name": "Post-peen CMM",           "cycle_time": 4,  "row": "top"},
    12: {"name": "Final CMM",               "cycle_time": 4,  "row": "top"},
    13: {"name": "Clear Overspray",         "cycle_time": 14, "row": "top"},
    14: {"name": "Final Inspection",        "cycle_time": 8,  "row": "top"},
    15: {"name": "Part Marking",            "cycle_time": 2,  "row": "top"},
    16: {"name": "Moment Weight",           "cycle_time": 3,  "row": "top"},
}

OPERATORS = {
    "Op1": {"stations": [1, 2, 3],       "color": (220, 50,  50 )},
    "Op2": {"stations": [10, 11, 6, 12], "color": (50,  100, 220)},
    "Op3": {"stations": [4, 8, 9],       "color": (50,  180, 90 )},
    "Op4": {"stations": [7, 13],         "color": (220, 140, 0  )},
    "Op5": {"stations": [5, 14, 15, 16], "color": (160, 50,  220)},
}

# Special boxes
SPECIAL_BOXES = {
    "Incoming":    {"label": "Incoming",    "row": "bottom", "position": "before",  "ref_station": 1,  "type": "counter", "start": 12},
    "HT_Out":      {"label": "HT Out",      "row": "bottom", "position": "between", "ref_station": 3,  "type": "buffer"},
    "HT_In":       {"label": "HT In",       "row": "bottom", "position": "between", "ref_station": 4,  "type": "buffer"},
    "Coating_In":  {"label": "Coating In",  "row": "top",    "position": "between", "ref_station": 11, "type": "buffer"},
    "Coating_Out": {"label": "Coating Out", "row": "top",    "position": "between", "ref_station": 12, "type": "buffer"},
    "Packing":     {"label": "Packing",     "row": "top",    "position": "after",   "ref_station": 16, "type": "counter", "start": 0},
}

# Part flow rules
# pickup: where operator gets part at start of that station
# dropoff: where operator leaves part after finishing that station
PART_FLOW = {
    "Op1": {
        "start_part": True,
        "pickup_from": "Incoming",
        "stations": {
            1: {"carry": True,  "dropoff": None},
            2: {"carry": True,  "dropoff": None},
            3: {"carry": True,  "dropoff": "HT_Out"},
        }
    },
    "Op2": {
        "start_part": True,
        "pickup_from": None,
        "stations": {
            10: {"carry": True,  "dropoff": None},
            11: {"carry": True,  "dropoff": "Coating_In"},
            6:  {"carry": False, "dropoff": "S7"},
            12: {"carry": False, "pickup": "Coating_Out", "dropoff": None},
        }
    },
    "Op3": {
        "start_part": True,
        "pickup_from": "HT_In",
        "stations": {
            4: {"carry": True,  "dropoff": None},
            8: {"carry": True,  "dropoff": None},
            9: {"carry": True,  "dropoff": "S10"},
        }
    },
    "Op4": {
        "start_part": True,
        "pickup_from": "S7",
        "stations": {
            7:  {"carry": True, "dropoff": None},
            13: {"carry": True, "dropoff": "S14"},
        }
    },
    "Op5": {
        "start_part": True,
        "pickup_from": None,
        "stations": {
            5:  {"carry": True, "dropoff": "S6"},
            14: {"carry": True, "pickup": "S14", "dropoff": None},
            15: {"carry": True, "dropoff": None},
            16: {"carry": True, "dropoff": "Packing"},
        }
    },
}

WINDOW_WIDTH   = 1900
WINDOW_HEIGHT  = 820
STATION_WIDTH  = 120
STATION_HEIGHT = 75
BOTTOM_ROW_Y   = 430
TOP_ROW_Y      = 300
ROW_START_X    = 20
ROW_GAP        = 148
BOX_WIDTH      = 100
BOX_HEIGHT     = 75