"""Persistent dimensions are optional, non-simulation annotations."""
import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scenario_schema import validate_scenario, ScenarioValidationError

class DimensionSchemaTests(unittest.TestCase):
    def base(self):
        return {'schema_version':2,'takt_time':30,'stations':{},'operators':{},'boxes':{}}

    def test_backward_compatible_missing_dimensions(self):
        scenario=self.base()
        self.assertEqual(validate_scenario(scenario, require_runnable=False),scenario)

    def test_valid_dimension_round_trip(self):
        scenario=self.base()
        scenario['dimensions']={'dim_1':{'x':2,'y':4,'x2':152,'y2':4,
            'start_anchor':{'type':'station','id':'1','rx':0,'ry':0},
            'end_anchor':{'type':'station','id':'1','rx':1,'ry':0}}}
        self.assertEqual(validate_scenario(scenario,require_runnable=False)['dimensions'],scenario['dimensions'])

    def test_offset_is_saved_and_must_be_finite(self):
        scenario=self.base()
        scenario['dimensions']={'dim_1':{'x':10,'y':5,'x2':50,'y2':5,'offset':-35}}
        self.assertEqual(validate_scenario(scenario,require_runnable=False)['dimensions']['dim_1']['offset'],-35)
        for bad in [float('nan'),float('inf'),'35',None]:
            scenario['dimensions']['dim_1']['offset']=bad
            with self.subTest(bad=bad),self.assertRaises(ScenarioValidationError):
                validate_scenario(scenario,require_runnable=False)

    def test_invalid_coordinates_are_rejected(self):
        for field,value in [('x',float('nan')),('y','10'),('x2',float('inf')),('y2',None)]:
            with self.subTest(field=field):
                scenario=self.base()
                scenario['dimensions']={'dim_1':{'x':1,'y':2,'x2':5,'y2':8}}
                scenario['dimensions']['dim_1'][field]=value
                with self.assertRaises(ScenarioValidationError):
                    validate_scenario(scenario,require_runnable=False)

    def test_bad_anchor_rejected(self):
        for anchor in [{'type':'operator','id':'Op1','rx':0,'ry':0},
            {'type':'station','id':'1','rx':3,'ry':0},
            {'type':'box','id':'__proto__','rx':0,'ry':1}]:
            with self.subTest(anchor=anchor):
                scenario=self.base()
                scenario['dimensions']={'dim_1':{'x':1,'y':2,'x2':5,'y2':8,'start_anchor':anchor}}
                with self.assertRaises(ScenarioValidationError):
                    validate_scenario(scenario,require_runnable=False)

if __name__=='__main__':unittest.main()
