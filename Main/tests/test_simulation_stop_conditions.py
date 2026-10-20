"""Runtime safeguards. Run in a project environment with Flask and SimPy installed.

These scenarios use the unchanged operator Pick/Work/Drop format to verify
that abnormal material flow stops as a red blocked event rather than success.
"""
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    from simulation import run_scenario_simulation
except ModuleNotFoundError as exc:
    if exc.name != 'simpy':
        raise
    run_scenario_simulation = None


def station(has_part=False, manual=0.1, auto=0):
    return {'name':'S1','x':180,'y':160,'w':150,'h':96,'has_part':has_part,
            'processes':[{'id':'p1','name':'Work','manual_time':manual,'auto_time':auto}]}


def operator(sequence, x=180, y=160):
    return {'name':'Op1','x':x,'y':y,'color':[20,90,190],'sequence':sequence}


def scenario(operators, *, stations=None, boxes=None, takt=1):
    return {'schema_version':2,'takt_time':takt,'layout_scale_px_per_m':50,
            'walking_speed_m_per_s':1.2,'stations':stations if stations is not None else {'1':station()},
            'operators':operators,'boxes':boxes if boxes is not None else {}}


@unittest.skipIf(run_scenario_simulation is None, "SimPy not installed")
class SimulationStopTests(unittest.TestCase):
    def assert_error(self, data, fragment):
        events, _ = run_scenario_simulation(data)
        self.assertEqual(events[-1]['status'],'blocked',events[-6:])
        self.assertIn(fragment.lower(),events[-1]['reason'].lower())
        self.assertNotIn('simulation_complete',[e['status'] for e in events])
        self.assertTrue(all(a['time'] <= b['time'] for a,b in zip(events,events[1:])))

    def test_waiting_on_empty_station_stops(self):
        events, _ = run_scenario_simulation(scenario(
            {'Op1':operator([{'action':'work','loc':'1','process':'p1'}])}, takt=10))
        self.assertEqual(events[-1]['status'], 'blocked')
        self.assertIn('Op1, step 1', events[-1]['reason'])
        self.assertIn('5 simulation minutes', events[-1]['reason'])
        arrived = next(e for e in events if e['status'] == 'arrived' and e['operator'] == 'Op1')
        self.assertAlmostEqual(events[-1]['time'] - arrived['time'], 5.0, places=6)

    def test_empty_swip_stops(self):
        boxes={'swip':{'name':'SWIP','type':'swip','x':100,'y':300,'w':80,'h':60,'has_part':False},
               'out':{'name':'OUT','type':'out','x':340,'y':300,'w':80,'h':60,'capacity':150}}
        events, _ = run_scenario_simulation(scenario(
            {'Op1':operator([{'action':'pick','loc':'swip'},{'action':'drop','loc':'out'}])},
            boxes=boxes, takt=10))
        self.assertEqual(events[-1]['status'], 'blocked')
        self.assertIn('SWIP box is empty', events[-1]['reason'])
        self.assertIn('Op1, step 1', events[-1]['reason'])
        arrived = next(e for e in events if e['status'] == 'arrived' and e['operator'] == 'Op1')
        self.assertAlmostEqual(events[-1]['time'], arrived['time'], places=6)
        self.assertFalse(any(e['status'] == 'waiting' for e in events))

    def test_one_operator_times_out_while_another_keeps_producing(self):
        # Another operator's successful repeated work must not reset the
        # waiting operator's five-minute timer.
        boxes={
            'in':{'name':'IN','type':'in','x':20,'y':100,'w':80,'h':60,'start_count':150},
            'out':{'name':'OUT','type':'out','x':300,'y':100,'w':80,'h':60,'capacity':150},
        }
        operators={
            'Op1':operator([{'action':'work','loc':'1','process':'p1'}]),
            'Op2':operator([{'action':'pick','loc':'in'},{'action':'drop','loc':'out'}], x=60, y=130),
        }
        # Finished output at <=takt avoids interfering with the wait diagnosis.
        events,_ = run_scenario_simulation(scenario(operators,boxes=boxes,takt=2))
        self.assertEqual(events[-1]['status'], 'blocked')
        self.assertEqual(events[-1]['operator'], 'Op1')
        self.assertIn('5 simulation minutes', events[-1]['reason'])
        self.assertGreater(sum(e['status'] == 'dropoff' for e in events), 1)

    def test_station_handoff_completes_before_five_minute_limit(self):
        boxes={'in':{'name':'IN','type':'in','x':30,'y':160,'w':80,'h':60,'start_count':150},
               'out':{'name':'OUT','type':'out','x':440,'y':160,'w':80,'h':60,'capacity':150}}
        ops={
            'Op1':operator([{'action':'work','loc':'1','process':'p1'},
                            {'action':'pick','loc':'1'}, {'action':'drop','loc':'out'}], x=230,y=200),
            'Op2':operator([{'action':'pick','loc':'in'},{'action':'drop','loc':'1'}],x=70,y=180),
        }
        events,_=run_scenario_simulation(scenario(ops, boxes=boxes, takt=2))
        waits=[e for e in events if e['status']=='waiting' and e['operator']=='Op1']
        starts=[e for e in events if e['status']=='manual_start' and e['operator']=='Op1']
        self.assertTrue(waits and starts, events[:20])
        self.assertLess(starts[0]['time']-waits[0]['time'], 5)
        self.assertNotIn('5 simulation minutes', ' '.join(e.get('reason','') for e in events))

    def test_pick_unprocessed_part_without_completion_gate(self):
        ops={'Op1':operator([{'action':'pick','loc':'1','wait_for_process':True}, {'action':'drop','loc':'out'}]),
             'Op2':operator([{'action':'work','loc':'1','process':'p1'}], x=2000,y=160)}
        boxes={'out':{'name':'OUT','type':'out','x':400,'y':300,'w':80,'h':60,'capacity':150}}
        events,_ = run_scenario_simulation(scenario(ops, stations={'1':station(True)}, boxes=boxes))
        pickups=[e for e in events if e['status']=='pickup' and e['loc']=='1' and e['operator']=='Op1']
        self.assertTrue(pickups, events[:15])
        self.assertFalse(any(e['status']=='process_complete' and e['time'] <= pickups[0]['time'] for e in events))
        self.assertNotIn('incomplete station processing', ' '.join(str(e.get('reason', '')) for e in events).lower())

    def test_drop_into_occupied_station_stops_immediately(self):
        boxes={'in':{'name':'IN','type':'in','x':20,'y':160,'w':80,'h':60,'start_count':20}}
        ops={'Op1':operator([{'action':'pick','loc':'in'}, {'action':'drop','loc':'1'}], x=55,y=180)}
        events,_=run_scenario_simulation(scenario(ops,stations={'1':station(True)},boxes=boxes,takt=10))
        self.assertEqual(events[-1]['status'], 'blocked')
        self.assertIn('already contains a part', events[-1]['reason'])
        self.assertIn('step 2', events[-1]['reason'])
        self.assertFalse(any(e['status']=='waiting' and e['loc']=='1' for e in events))

    def test_drop_into_processing_station_stops_immediately(self):
        boxes={'in':{'name':'IN','type':'in','x':0,'y':160,'w':80,'h':60,'start_count':20}}
        ops={
            'Op1':operator([{'action':'work','loc':'1','process':'p1'}],x=200,y=150),
            'Op2':operator([{'action':'pick','loc':'in'}, {'action':'drop','loc':'1'}],x=40,y=180),
        }
        events,_=run_scenario_simulation(scenario(ops,stations={'1':station(True, manual=0.1, auto=20)},boxes=boxes,takt=10))
        self.assertEqual(events[-1]['status'],'blocked')
        self.assertIn('still processing', events[-1]['reason'])
        self.assertEqual(events[-1]['operator'],'Op2')
        self.assertFalse(any(e['status']=='waiting' and e['loc']=='1' for e in events))

    def test_pick_during_processing_stops_instead_of_waiting(self):
        boxes={'out':{'name':'OUT','type':'out','x':360,'y':320,'w':80,'h':60,'capacity':150}}
        ops={
            'Op1':operator([{'action':'work','loc':'1','process':'p1'}],x=200,y=150),
            'Op2':operator([{'action':'pick','loc':'1'}, {'action':'drop','loc':'out'}],x=70,y=250),
        }
        events,_=run_scenario_simulation(scenario(ops,stations={'1':station(True, manual=0.1, auto=20)},boxes=boxes,takt=10))
        self.assertEqual(events[-1]['status'],'blocked')
        self.assertIn('still processing', events[-1]['reason'])
        self.assertEqual(events[-1]['operator'],'Op2')

    def test_independent_station_processes_can_run_without_sequence(self):
        station_def=station(True)
        station_def['processes'].append({'id':'p2','name':'Second Work','manual_time':0.2,'auto_time':0})
        ops={'Op1':operator([{'action':'work','loc':'1','process':'p2'}, {'action':'work','loc':'1','process':'p1'}],x=200,y=150)}
        events,_=run_scenario_simulation(scenario(ops,stations={'1':station_def},takt=10))
        completes=[e['process'] for e in events if e['status']=='process_complete' and e['operator']=='Op1']
        self.assertEqual(completes[:2], ['p2','p1'])

    def test_duplicate_work_on_same_part_stops(self):
        self.assert_error(scenario({'Op1':operator([{'action':'work','loc':'1','process':'p1'}])},stations={'1':station(True)}), 'already completed')

    def test_behind_takt_stops(self):
        boxes={'in':{'name':'IN','type':'in','x':0,'y':0,'w':80,'h':60,'start_count':150},
               'out':{'name':'OUT','type':'out','x':10000,'y':0,'w':80,'h':60,'capacity':150}}
        ops={'Op1':operator([{'action':'pick','loc':'in'},{'action':'drop','loc':'out'}], x=40,y=30)}
        self.assert_error(scenario(ops,stations={'1':station()},boxes=boxes), 'below takt')

    def test_valid_output_stream_finishes(self):
        boxes={'in':{'name':'IN','type':'in','x':20,'y':300,'w':80,'h':60,'start_count':150},
               'out':{'name':'OUT','type':'out','x':220,'y':300,'w':80,'h':60,'capacity':150}}
        ops={'Op1':operator([{'action':'pick','loc':'in'},{'action':'drop','loc':'out'}],x=60,y=330)}
        events,_=run_scenario_simulation(scenario(ops,boxes=boxes,takt=3))
        self.assertEqual(events[-1]['status'],'simulation_complete',events[-5:])


if __name__=='__main__':unittest.main()
