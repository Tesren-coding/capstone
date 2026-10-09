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
    6:  {"name": "T800 Machining",          "cycle_time": 7, "row": "bottom"},
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
    "Op1": {"color": (220, 50,  50 )},
    "Op2": {"color": (50,  100, 220)},
    "Op3": {"color": (50,  180, 90 )},
    "Op4": {"color": (220, 140, 0  )},
    "Op5": {"color": (160, 50,  220)},
}

SPECIAL_BOXES = {
    "Incoming":    {"label": "Incoming",    "row": "bottom", "type": "counter", "start": 12},
    "HT_Out":      {"label": "HT Out",      "row": "bottom", "type": "buffer"},
    "HT_In":       {"label": "HT In",       "row": "bottom", "type": "buffer"},
    "Coating_In":  {"label": "Coating In",  "row": "top",    "type": "buffer"},
    "Coating_Out": {"label": "Coating Out", "row": "top",    "type": "buffer"},
    "Packing":     {"label": "Packing",     "row": "top",    "type": "counter", "start": 0},
    "SWIP_1":      {"label": "SWIP 1",      "row": "bottom", "type": "image",   "image": "images/SWIP.png"},
    "SWIP_2":      {"label": "SWIP 2",      "row": "bottom", "type": "image",   "image": "images/SWIP.png"},
    "SWIP_3":      {"label": "SWIP 3",      "row": "bottom", "type": "image",   "image": "images/SWIP.png"},
    "SWIP_4":      {"label": "SWIP 4",      "row": "top",    "type": "image",   "image": "images/SWIP.png"},
    "SWIP_5":      {"label": "SWIP 5",      "row": "top",    "type": "image",   "image": "images/SWIP.png"},
    "SWIP_6":      {"label": "SWIP 6",      "row": "top",    "type": "image",   "image": "images/SWIP.png"},
    "SWIP_7":      {"label": "SWIP 7",      "row": "top",    "type": "image",   "image": "images/SWIP.png"},
}

# ============================================================
# Operator sequences
# Each step: location, action
# location: station ID (int) or box key (str)
# action: "work", "pick", "drop"
# ============================================================
OP_SEQUENCES = {
    "Op1": [
        {"loc": "Incoming", "action": "pick"},
        {"loc": 1,          "action": "work"},
        {"loc": 2,          "action": "work"},
        {"loc": 3,          "action": "work"},
        {"loc": "HT_Out",   "action": "drop"},
    ],
    "Op2": [
        {"loc": 10,          "action": "work"},
        {"loc": "SWIP_5",    "action": "drop"},
        {"loc": "SWIP_4",    "action": "pick"},
        {"loc": 10,          "action": "work"},
        {"loc": 11,          "action": "pick"},
        {"loc": "Coating_Out","action": "drop"},
        {"loc": "Coating_In","action": "pick"},
        {"loc": 12,          "action": "work"},
        {"loc": 6,           "action": "pick"},
        {"loc": "SWIP_3",    "action": "drop"},
        {"loc": "SWIP_2",    "action": "pick"},
        {"loc": 6,           "action": "work"},
        {"loc": 12,          "action": "pick"},
        {"loc": "SWIP_6",    "action": "drop"},
        {"loc": "SWIP_5",    "action": "pick"},
        {"loc": 11,          "action": "work"},
    ],
    "Op3": [
        {"loc": "HT_In",  "action": "pick"},
        {"loc": 4,        "action": "work"},
        {"loc": "SWIP_1", "action": "drop"},
        {"loc": 8,        "action": "work"},
        {"loc": 9,        "action": "work"},
        {"loc": "SWIP_4", "action": "drop"},
    ],
    "Op4": [
        {"loc": "SWIP_3", "action": "pick"},
        {"loc": 7,        "action": "work"},
        {"loc": 8,        "action": "drop"},
        {"loc": "SWIP_6", "action": "pick"},
        {"loc": 13,       "action": "work"},
        {"loc": "SWIP_7", "action": "drop"},
    ],
    "Op5": [
        {"loc": "SWIP_1", "action": "pick"},
        {"loc": 5,        "action": "work"},
        {"loc": "SWIP_2", "action": "drop"},
        {"loc": "SWIP_7", "action": "pick"},
        {"loc": 14,       "action": "work"},
        {"loc": 15,       "action": "work"},
        {"loc": 16,       "action": "work"},
        {"loc": "Packing","action": "drop"},
    ],
}

# starting part for each operator
OP_START_PART = {
    "Op1": True,
    "Op2": True,
    "Op3": True,
    "Op4": True,
    "Op5": True,
}

WINDOW_WIDTH   = 1900
WINDOW_HEIGHT  = 820
STATION_WIDTH  = 120
STATION_HEIGHT = 75
BOTTOM_ROW_Y   = 480
TOP_ROW_Y      = 280
ROW_START_X    = 20
ROW_GAP        = 130
BOX_WIDTH      = 100
BOX_HEIGHT     = 75