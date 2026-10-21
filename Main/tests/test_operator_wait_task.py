"""Regression coverage for deliberate operator Wait tasks.

The SimPy assertions run when dependencies are installed in the normal app
runtime. Schema/export checks are independent of SimPy.
"""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scenario_schema import validate_scenario, ScenarioValidationError
from standard_work_exports import planned_steps, movement_visits

try:
    from simulation import run_scenario_simulation
except ModuleNotFoundError as exc:
    if exc.name != 'simpy': raise
    run_scenario_simulation = None


def sample(seq, *, takt=10, station_part=True):
    return {
        'schema_version':2, 'takt_time':takt,
        'stations':{'1':{'name':'Inspection','x':0,'y':0,'w':150,'h':96,
                 'has_part':station_part,'processes':[{'id':'p1','name':'Check','manual_time':0.2,'auto_time':0}]}},
        'operators':{'Op1':{'name':'Op1','x':0,'y':0,'color':[20,90,190], 'sequence':seq}},
        'boxes':{},
    }


class WaitTaskSchemaTests(unittest.TestCase):
    def test_valid_wait_without_location(self):
        src=sample([{'action':'wait','duration':7.5},{'action':'work','loc':'1','process':'p1'}])
        data=validate_scenario(src)
        self.assertEqual(data['operators']['Op1']['sequence'][0],{'action':'wait','duration':7.5})
        self.assertEqual(planned_steps(data,'Op1')[0]['description'], 'Wait / idle for 7.5 min (no movement or work)')
        self.assertEqual([s['loc'] for s in movement_visits(data,'Op1')],['1'])

    def test_reject_invalid_wait_duration(self):
        for duration in [0,-1,'2',None,True,float('inf')]:
            with self.subTest(duration=duration),self.assertRaises(ScenarioValidationError):
                validate_scenario(sample([{'action':'wait','duration':duration}]))

    def test_wait_between_pick_and_drop_keeps_part_carrying(self):
        data=sample([{'action':'pick','loc':'1'},{'action':'wait','duration':6},{'action':'drop','loc':'1'}])
        self.assertEqual(validate_scenario(data)['operators']['Op1']['sequence'][1]['action'],'wait')


@unittest.skipIf(run_scenario_simulation is None,'SimPy not installed')
class WaitTaskRuntimeTests(unittest.TestCase):
    def test_wait_more_than_five_minutes_is_not_blocked(self):
        data=sample([{'action':'wait','duration':8},{'action':'work','loc':'1','process':'p1'}],takt=12)
        events,_=run_scenario_simulation(data)
        begins=[e for e in events if e['status']=='planned_wait_start']
        ends=[e for e in events if e['status']=='planned_wait_end']
        self.assertTrue(begins and ends)
        self.assertAlmostEqual(ends[0]['time']-begins[0]['time'],8)
        self.assertFalse(any(e['status']=='blocked' for e in events),events[-6:])
        first_work=next(e for e in events if e['status']=='manual_start')
        self.assertGreaterEqual(first_work['time'],8)
        self.assertFalse(any(e['status']=='moving' and begins[0]['time']<e['time']<ends[0]['time'] for e in events))

    def test_wait_has_no_unplanned_move(self):
        data=sample([{'action':'wait','duration':2},{'action':'pick','loc':'1'},{'action':'drop','loc':'1'}],takt=10)
        events,_=run_scenario_simulation(data)
        start=next(e for e in events if e['status']=='planned_wait_start')
        end=next(e for e in events if e['status']=='planned_wait_end')
        self.assertEqual(end['time']-start['time'],2)
        self.assertFalse(any(e['status']=='arrived' and e['time']<end['time'] for e in events))


if __name__=='__main__':unittest.main()
