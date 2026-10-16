"""Standalone direction-marker validation tests (no Flask/SimPy dependency)."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scenario_schema import validate_scenario, ScenarioValidationError


def base():
    return {'schema_version': 2, 'takt_time': 30, 'stations': {}, 'operators': {},
        'boxes': {'DIRECTION_1': {'type': 'direction', 'name': 'Line Direction',
            'x': 100, 'y': 160, 'w': 220, 'h': 28}}}


class DirectionSchemaTests(unittest.TestCase):
    def test_old_marker_still_valid(self):
        data = base()
        self.assertEqual(validate_scenario(data, require_runnable=False), data)

    def test_flips_rotation_roundtrip(self):
        data = base()
        data['boxes']['DIRECTION_1'].update(rotation=270, flip_horizontal=True, flip_vertical=False)
        normalized = validate_scenario(data, require_runnable=False)
        self.assertEqual(normalized['boxes']['DIRECTION_1'], data['boxes']['DIRECTION_1'])

    def test_bad_metadata_rejected(self):
        for field, value in [('rotation', 'left'), ('rotation', float('inf')),
                             ('flip_horizontal', 'true'), ('flip_vertical', 1)]:
            with self.subTest(field=field):
                data = base()
                data['boxes']['DIRECTION_1'][field] = value
                with self.assertRaises(ScenarioValidationError):
                    validate_scenario(data, require_runnable=False)

    def test_direction_not_a_pick_location(self):
        data = base()
        data['stations']['1'] = {'x':100, 'y':250, 'w':150,'h':96, 'name':'Test',
             'has_part':True, 'processes':[{'id':'p1','name':'Test','manual_time':1,'auto_time':0}]}
        data['operators']['Op1'] = {'x':100,'y':300,'name':'Op1','color':[10,20,30],
            'sequence':[{'action':'pick','loc':'DIRECTION_1'}, {'action':'drop','loc':'1'}]}
        with self.assertRaisesRegex(ScenarioValidationError, 'visual marker'):
            validate_scenario(data)


if __name__ == '__main__':
    unittest.main()
