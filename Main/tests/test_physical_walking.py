"""Unit tests for physical distance, speed and standing points (no Flask/SimPy needed)."""
from copy import deepcopy
import math
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from walking_geometry import box_center, station_destination, standing_point, walking_metrics
from scenario_schema import validate_scenario, ScenarioValidationError


def draft():
    return {'schema_version': 2, 'takt_time': 30,
            'layout_scale_px_per_m': 50, 'walking_speed_m_per_s': 1.2,
            'stations': {'1': {'x': 100, 'y': 200, 'w': 150, 'h': 96, 'name': 'Weld', 'has_part': True, 'cycle_time': 1,
                               'processes': [{'id':'p1','name':'Weld','manual_time':1,'auto_time':0}]}},
            'operators': {'Op1': {'name':'Op1','color':[200,50,50],'x':175,'y':174,
                                    'attached_to':{'station_id':'1','side':'top'},
                                    'sequence':[{'loc':'1','action':'work','process':'p1','standing_side':'left'}]}},
            'boxes': {}}


class PhysicalWalkingTests(unittest.TestCase):
    def test_side_coordinates_match_builder_snap_slots(self):
        station = draft()['stations']['1']
        self.assertEqual(standing_point(station, 'top'), {'x':175,'y':174})
        self.assertEqual(standing_point(station, 'right'), {'x':276,'y':248})
        self.assertEqual(standing_point(station, 'bottom'), {'x':175,'y':322})
        self.assertEqual(standing_point(station, 'left'), {'x':74,'y':248})

    def test_in_out_swip_all_use_center_not_side(self):
        for kind in ('in', 'out', 'swip'):
            with self.subTest(kind=kind):
                box={'type': kind, 'x': 250, 'y': 400, 'w': 90, 'h': 60}
                self.assertEqual(box_center(box), {'x':295, 'y':430})
                distance, minutes=walking_metrics({'x':245,'y':430},box_center(box),50,1.2)
                self.assertAlmostEqual(distance,1)
                self.assertAlmostEqual(minutes*60,1/1.2)

    def test_explicit_side_overrides_home_attachment(self):
        data = draft(); op=data['operators']['Op1']
        p=station_destination(data['stations'],'1',op['sequence'][0], {'x':175,'y':174}, op)
        self.assertEqual(p,{'x':74,'y':248})

    def test_auto_prefers_anchor_then_nearest_for_other_stations(self):
        data=draft(); op=data['operators']['Op1']; step={'loc':'1','action':'work','process':'p1'}
        self.assertEqual(station_destination(data['stations'],'1',step,{'x':300,'y':260},op),{'x':175,'y':174})
        del op['attached_to']
        self.assertEqual(station_destination(data['stations'],'1',step,{'x':300,'y':260},op),{'x':276,'y':248})

    def test_units_and_walking_speed_in_simulated_minutes(self):
        start={'x':0,'y':0}; end={'x':150,'y':0}
        distance, minutes=walking_metrics(start,end,50,1.2)
        self.assertAlmostEqual(distance,3)
        self.assertAlmostEqual(minutes*60,2.5)
        self.assertAlmostEqual(walking_metrics(start,end,100,1.2)[0],1.5)
        self.assertAlmostEqual(walking_metrics(start,end,50,0.6)[1],minutes*2)

    def test_schema_allows_optional_fields_on_old_saves(self):
        old=draft();old.pop('layout_scale_px_per_m');old.pop('walking_speed_m_per_s')
        old['operators']['Op1']['sequence'][0].pop('standing_side')
        self.assertEqual(validate_scenario(old), old)
        self.assertEqual(validate_scenario(draft()),draft())

    def test_invalid_speed_scale_or_side_rejected(self):
        for field, value in [('walking_speed_m_per_s',0),('walking_speed_m_per_s',-1),
                             ('walking_speed_m_per_s',6),('layout_scale_px_per_m',0),
                             ('layout_scale_px_per_m',float('nan'))]:
            case=draft();case[field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ScenarioValidationError):
                validate_scenario(case)
        case=draft();case['operators']['Op1']['sequence'][0]['standing_side']='middle'
        with self.assertRaises(ScenarioValidationError):validate_scenario(case)


if __name__ == '__main__':
    unittest.main()
