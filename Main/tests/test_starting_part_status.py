"""Regression for station starting inventory completion (no process-route changes).

Run:
  python -m unittest discover -s tests -p 'test_starting_part_status.py'
SimPy tests automatically run when the application's dependencies are installed.
"""
from copy import deepcopy
import unittest

from scenario_schema import ScenarioValidationError, normalize_scenario, validate_scenario

try:
    from simulation import run_scenario_simulation
except ModuleNotFoundError as exc:
    if exc.name != 'simpy':
        raise
    run_scenario_simulation = None


def scenario(processed=None):
    station = {'name': 'Inspection', 'x': 160, 'y': 110, 'w': 150, 'h': 96,
               'has_part': True,
               'processes': [{'id': 'p1', 'name': 'Inspect', 'manual_time': 0.5, 'auto_time': 0}]}
    if processed is not None:
        station['starting_part_processed'] = processed
    return {'schema_version': 2, 'takt_time': 8,
            'stations': {'1': station},
            'operators': {
                'Op1': {'name': 'Op1', 'x': 220, 'y': 135, 'color': [10, 100, 220],
                        'sequence': [{'action': 'pick', 'loc': '1', 'wait_for_process': True},
                                     {'action': 'drop', 'loc': 'out'}]},
                'Op2': {'name': 'Op2', 'x': 500, 'y': 500, 'color': [200, 80, 40],
                        'sequence': [{'action': 'work', 'loc': '1', 'process': 'p1'}]},
            },
            'boxes': {'out': {'type': 'out', 'name': 'OUT', 'x': 350, 'y': 110,
                              'w': 85, 'h': 50, 'capacity': 150}}}


class StartingPartStatusContractTest(unittest.TestCase):
    def test_legacy_saves_default_unprocessed_without_mutating_original(self):
        original = scenario()
        snapshot = deepcopy(original)
        normalized = normalize_scenario(original)
        self.assertEqual(normalized['stations']['1']['starting_part_processed'], False)
        self.assertEqual(original, snapshot)
        self.assertEqual(normalize_scenario(normalized), normalized)
        self.assertFalse(validate_scenario(original)['stations']['1']['starting_part_processed'])

    def test_processed_is_boolean_and_kept_in_validated_copy(self):
        self.assertTrue(validate_scenario(scenario(True))['stations']['1']['starting_part_processed'])
        self.assertFalse(validate_scenario(scenario(False))['stations']['1']['starting_part_processed'])
        for invalid in ('processed', 1, None, {}, []):
            with self.subTest(invalid=invalid):
                data = scenario()
                data['stations']['1']['starting_part_processed'] = invalid
                with self.assertRaises(ScenarioValidationError) as error:
                    validate_scenario(data)
                self.assertIn('starting part status', str(error.exception))

    @unittest.skipIf(run_scenario_simulation is None, 'SimPy not installed')
    def test_unprocessed_start_can_be_picked_without_station_work(self):
        events, _ = run_scenario_simulation(scenario(False))
        events = [event for event in events if event['loc'] == '1']
        first_pickup = next(e for e in events if e['status'] == 'pickup')
        self.assertFalse(any(e['status'] == 'process_complete' and e['time'] <= first_pickup['time']
                             for e in events))

    @unittest.skipIf(run_scenario_simulation is None, 'SimPy not installed')
    def test_new_part_delivered_later_is_unprocessed(self):
        data = scenario(True)
        data['takt_time'] = 100
        data['boxes']['in'] = {'type': 'in', 'name': 'IN', 'x': 120, 'y': 380,
                                'w': 65, 'h': 60, 'start_count': 15}
        data['operators']['Op2']['x'] = 120
        data['operators']['Op2']['y'] = 380
        data['operators']['Op2']['sequence'] = [
            {'action': 'pick', 'loc': 'in'}, {'action': 'drop', 'loc': '1'}]
        data['operators']['Op3'] = {'name': 'Op3', 'x': 2000, 'y': 1000,
                                    'color': [90, 200, 80],
                                    'sequence': [{'action': 'work', 'loc': '1', 'process': 'p1'}]}
        events, _ = run_scenario_simulation(data)
        pickups = [(i,e) for i,e in enumerate(events) if e['status']=='pickup' and e['loc']=='1']
        self.assertGreaterEqual(len(pickups), 2, events[-15:])
        # The incoming part starts unprocessed even when the initial part
        # was marked processed; Op3 is allowed to process its own assigned work.
        self.assertTrue(any(e['status']=='dropoff' and e['loc']=='1' for e in events), events[:20])
        self.assertTrue(any(e['status']=='process_complete' and e['loc']=='1' for e in events), events[:30])

    @unittest.skipIf(run_scenario_simulation is None, 'SimPy not installed')
    def test_processed_start_may_be_picked_before_station_work(self):
        events, _ = run_scenario_simulation(scenario(True))
        pickups = [e for e in events if e['status'] == 'pickup' and e['loc'] == '1']
        self.assertTrue(pickups, events[:12])
        # No station-wide process gate; part may be collected when idle.
        self.assertFalse([e for e in events if e['status'] == 'process_complete'
                          and e['time'] <= pickups[0]['time']])


if __name__ == '__main__':
    unittest.main()
