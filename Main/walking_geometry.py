"""Physical layout geometry shared by SimPy travel events and tests.

All coordinates are scenario/world units, independent of browser zoom.
"""
import math

DEFAULT_LAYOUT_SCALE_PX_PER_M = 50.0
DEFAULT_WALK_SPEED_M_PER_S = 1.2
OPERATOR_STAND_OFFSET_PX = 26.0  # 16px operator radius + 10px clearance
STANDING_SIDES = ('top', 'right', 'bottom', 'left')


def standing_point(station, side):
    """Center of a station side, with clearance for the operator icon."""
    x, y, w, h = (station[k] for k in ('x', 'y', 'w', 'h'))
    points = {
        'top': {'x': x + w / 2, 'y': y - OPERATOR_STAND_OFFSET_PX},
        'right': {'x': x + w + OPERATOR_STAND_OFFSET_PX, 'y': y + h / 2},
        'bottom': {'x': x + w / 2, 'y': y + h + OPERATOR_STAND_OFFSET_PX},
        'left': {'x': x - OPERATOR_STAND_OFFSET_PX, 'y': y + h / 2},
    }
    return points[side]


def station_destination(stations, station_id, step, position, definition):
    """Honor a per-step side; otherwise use operator home side or nearest side."""
    station = stations[station_id]
    side = step.get('standing_side')
    if side is None:
        home_anchor = definition.get('attached_to')
        if home_anchor and home_anchor['station_id'] == station_id:
            side = home_anchor['side']
        else:
            side = min(STANDING_SIDES, key=lambda candidate: math.hypot(
                standing_point(station, candidate)['x'] - position['x'],
                standing_point(station, candidate)['y'] - position['y']))
    return standing_point(station, side)


def box_center(box):
    """IN, OUT and SWIP boxes use their center as the travel destination."""
    return {'x': box['x'] + box['w'] / 2, 'y': box['y'] + box['h'] / 2}


def walking_metrics(start, target, pixels_per_meter, walking_speed_m_per_s):
    """Return (meters, simulated minutes) for straight-line travel."""
    distance_m = math.hypot(target['x'] - start['x'], target['y'] - start['y']) / pixels_per_meter
    return distance_m, distance_m / walking_speed_m_per_s / 60.0
