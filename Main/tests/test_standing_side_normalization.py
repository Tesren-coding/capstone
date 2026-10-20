"""Regression for legacy station-side hints on IN/OUT/SWIP box steps.
Run: python -m unittest discover -s tests -p 'test_standing_side_normalization.py'
"""
import copy
import unittest
from scenario_schema import ScenarioValidationError, validate_scenario, normalize_scenario


def sample():
    return {
        'schema_version': 2, 'takt_time': 30,
        'stations': {'1': {'name': 'Inspection', 'x': 100, 'y': 100, 'w': 150, 'h': 96,
                           'has_part': False,
                           'processes': [{'id': 'p1', 'name': 'Inspect', 'manual_time': 2, 'auto_time': 0}]}},
        'boxes': {
            'IN_1': {'name': 'IN', 'type': 'in', 'x': 0, 'y': 100, 'w': 65, 'h': 60, 'start_count': 3},
            'SWIP_1': {'name': 'SWIP', 'type': 'swip', 'x': 310, 'y': 100, 'w': 65, 'h': 60, 'has_part': False},
            'OUT_1': {'name': 'OUT', 'type': 'out', 'x': 415, 'y': 100, 'w': 65, 'h': 60, 'capacity': 50},
        },
        'operators': {'Op6': {'name': 'Op6', 'x': 75, 'y': 120, 'color': [40, 100, 190],
                             'sequence': [
                                 {'action': 'pick', 'loc': 'IN_1', 'standing_side': 'left'},
                                 {'action': 'drop', 'loc': '1', 'standing_side': 'right'},
                                 {'action': 'work', 'loc': '1', 'process': 'p1', 'standing_side': 'right'},
                                 {'action': 'pick', 'loc': '1', 'standing_side': 'right'},
                                 {'action': 'drop', 'loc': 'SWIP_1', 'standing_side': 'top'},
                                 {'action': 'pick', 'loc': 'SWIP_1', 'standing_side': 'bottom'},
                                 {'action': 'drop', 'loc': 'OUT_1', 'standing_side': 'left'},
                             ]}},
    }


class StandingSideNormalizationTest(unittest.TestCase):
    def test_box_side_ignored_in_both_runnable_and_draft(self):
        original = sample()
        unchanged = copy.deepcopy(original)
        for runnable in (False, True):
            normalized = validate_scenario(original, require_runnable=runnable)
            steps = normalized['operators']['Op6']['sequence']
            for idx in (0, 4, 5, 6):
                self.assertNotIn('standing_side', steps[idx])
            for idx in (1, 2, 3):
                self.assertEqual(steps[idx]['standing_side'], 'right')
        self.assertEqual(original, unchanged, 'normalization must never rewrite the user file')
        self.assertEqual(normalize_scenario(normalized), normalized)

    def test_invalid_station_side_still_rejected(self):
        data = sample()
        data['operators']['Op6']['sequence'][2]['standing_side'] = 'middle'
        with self.assertRaises(ScenarioValidationError) as err:
            validate_scenario(data)
        self.assertIn('standing side must be top, right, bottom or left', str(err.exception))

    def test_unknown_location_still_rejected(self):
        data = sample()
        data['operators']['Op6']['sequence'][5]['loc'] = 'missing'
        with self.assertRaises(ScenarioValidationError):
            validate_scenario(data)


if __name__ == '__main__':
    unittest.main()
