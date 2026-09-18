# ============================================================
# layout.py
# Calculates positions of stations and special boxes
# ============================================================

from data import (
    STATIONS,
    STATION_WIDTH, STATION_HEIGHT,
    BOTTOM_ROW_Y, TOP_ROW_Y,
    ROW_START_X, ROW_GAP,
    BOX_WIDTH, BOX_HEIGHT
)

BOTTOM_SEQUENCE = [
    ("box",     "Incoming"),
    ("station", 1),
    ("station", 2),
    ("station", 3),
    ("box",     "HT_Out"),
    ("box",     "HT_In"),
    ("station", 4),
    ("box",     "SWIP_1"),
    ("station", 5),
    ("box",     "SWIP_2"),
    ("station", 6),
    ("box",     "SWIP_3"),
    ("station", 7),
    ("station", 8),
    ("station", 9),
]

TOP_SEQUENCE = [
    ("box",     "Packing"),
    ("station", 16),
    ("station", 15),
    ("station", 14),
    ("box",     "SWIP_7"),
    ("station", 13),
    ("box",     "SWIP_6"),
    ("box",     "Coating_Out"),
    ("station", 12),
    ("station", 11),
    ("box",     "SWIP_5"),
    ("box",     "Coating_In"),
    ("station", 10),
    ("box",     "SWIP_4"),
]

def build_positions():
    station_positions = {}
    box_positions     = {}

    for i, (item_type, item_id) in enumerate(BOTTOM_SEQUENCE):
        x = ROW_START_X + i * ROW_GAP
        if item_type == "station":
            station_positions[item_id] = (
                x, BOTTOM_ROW_Y, STATION_WIDTH, STATION_HEIGHT
            )
        else:
            box_positions[item_id] = (
                x, BOTTOM_ROW_Y, BOX_WIDTH, BOX_HEIGHT
            )

    for i, (item_type, item_id) in enumerate(TOP_SEQUENCE):
        x = ROW_START_X + i * ROW_GAP
        if item_type == "station":
            station_positions[item_id] = (
                x, TOP_ROW_Y, STATION_WIDTH, STATION_HEIGHT
            )
        else:
            box_positions[item_id] = (
                x, TOP_ROW_Y, BOX_WIDTH, BOX_HEIGHT
            )

    station_centers = {
        sid: (x + STATION_WIDTH // 2, y + STATION_HEIGHT // 2)
        for sid, (x, y, w, h) in station_positions.items()
    }

    box_centers = {
        key: (x + BOX_WIDTH // 2, y + BOX_HEIGHT // 2)
        for key, (x, y, w, h) in box_positions.items()
    }

    return station_positions, box_positions, station_centers, box_centers