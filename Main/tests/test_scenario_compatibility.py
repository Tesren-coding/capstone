"""Run: python -m unittest discover -s tests -v"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as web
import scenario_schema as schema
from scenario_schema import ScenarioValidationError, normalize_scenario, validate_scenario
from scenario_store import ScenarioStore, ScenarioStorageError
from simulation import run_scenario_simulation


def legacy_scenario():
    return {'takt_time': 30,
            'stations': {'1': {'x': 500, 'y': 220, 'w': 150, 'h': 96, 'name': 'Machine', 'cycle_time': 2.5, 'has_part': True}},
            'operators': {'Op1': {'x': 575, 'y': 268, 'name': 'Operator 1', 'color': [30, 110, 210],
                                  'sequence': [{'action': 'work', 'loc': 1}]}},
            'boxes': {}, 'notes': {'owner': 'Example', 'units': 'minutes'}}


class CompatibilityTests(unittest.TestCase):
    def test_legacy_upgrade_and_input_preserved(self):
        original = legacy_scenario()
        before = deepcopy(original)
        upgraded = validate_scenario(original)
        self.assertEqual(original, before)
        self.assertEqual(upgraded['schema_version'], 2)
        self.assertEqual(upgraded['stations']['1']['processes'],
                         [{'id': 'p1', 'name': 'Process 1', 'manual_time': 2.5, 'auto_time': 0}])
        self.assertEqual(upgraded['operators']['Op1']['sequence'][0], {'action': 'work', 'loc': '1', 'process': 'p1'})
        self.assertEqual(upgraded['notes'], before['notes'])
        self.assertEqual(normalize_scenario(upgraded), upgraded)
        self.assertEqual(run_scenario_simulation(original), run_scenario_simulation(upgraded))

    def test_newer_and_invalid_versions_rejected(self):
        for version in [3, 999, True, '2', 0, -1, None]:
            data = legacy_scenario()
            data['schema_version'] = version
            with self.subTest(version=version), self.assertRaises(ScenarioValidationError):
                normalize_scenario(data)

    def test_current_format_is_not_silently_treated_as_legacy(self):
        data = legacy_scenario()
        data['schema_version'] = 2
        with self.assertRaises(ScenarioValidationError):
            validate_scenario(data, require_runnable=False)

    def test_migration_registry_runs_in_order_for_a_future_format(self):
        def next_migration(data):
            data['category'] = 'unspecified'
            return data
        with patch.object(schema, 'CURRENT_SCHEMA_VERSION', 3), patch.dict(schema.MIGRATIONS, {2: next_migration}):
            result = validate_scenario(legacy_scenario())
            self.assertEqual(result['schema_version'], 3)
            self.assertEqual(result['category'], 'unspecified')
            self.assertEqual(result['stations']['1']['processes'][0]['manual_time'], 2.5)

    def test_drafts_can_be_saved_but_cannot_run_with_unresolved_steps(self):
        draft = validate_scenario(legacy_scenario())
        draft['operators']['Op1']['sequence'] = [{'action': 'work', 'loc': '', 'process': ''}]
        self.assertEqual(validate_scenario(draft, require_runnable=False), draft)
        with self.assertRaises(ScenarioValidationError):
            validate_scenario(draft)
        empty = {'schema_version': 2, 'takt_time': 30, 'stations': {}, 'operators': {}, 'boxes': {}}
        validate_scenario(empty, require_runnable=False)
        with self.assertRaises(ScenarioValidationError):
            validate_scenario(empty)

    def test_direction_box_is_valid_non_inventory_decor(self):
        data = validate_scenario(legacy_scenario())
        data['boxes']['DIR_1'] = {'x': 120, 'y': 140, 'w': 220, 'h': 28, 'type': 'direction', 'name': 'Line Direction'}
        validated = validate_scenario(data)
        self.assertEqual(validated['boxes']['DIR_1']['type'], 'direction')
        events, _ = run_scenario_simulation(validated)
        self.assertEqual(events[-1]['status'], 'simulation_complete')

    def test_machine_concurrency_events_after_migration(self):
        data = validate_scenario(legacy_scenario())
        data['stations']['1']['processes'][0].update(manual_time=1, auto_time=4)
        data['stations']['2'] = {**data['stations']['1'], 'x': 900,
                                'processes': [{'id': 'p1', 'name': 'Bench', 'manual_time': 1, 'auto_time': 0}]}
        data['operators']['Op1']['sequence'].append({'action': 'work', 'loc': '2', 'process': 'p1'})
        events, _ = run_scenario_simulation(data)
        automatic = next(e for e in events if e['status'] == 'auto_start' and e['loc'] == '1')
        bench = next(e for e in events if e['status'] == 'manual_start' and e['loc'] == '2')
        self.assertLess(bench['time'], automatic['time'] + automatic['duration'])
        self.assertEqual([e['time'] for e in events], sorted(e['time'] for e in events))
        self.assertEqual(events[-1]['status'], 'simulation_complete')


class StorageAndRouteTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.store = ScenarioStore(self.directory)
        self.previous_store = web.scenario_store
        web.scenario_store = self.store
        self.client = web.app.test_client()

    def tearDown(self):
        web.scenario_store = self.previous_store
        self.temporary.cleanup()

    def test_load_and_duplicate_do_not_rewrite_original(self):
        original = json.dumps(legacy_scenario()).encode()
        (self.directory / 'old.json').write_bytes(original)
        loaded = self.store.load('old.json')
        self.assertEqual(loaded['migrated_from'], 1)
        self.assertEqual((self.directory / 'old.json').read_bytes(), original)
        copied = self.store.save('old.json', loaded['scenario'], 'duplicate')
        self.assertEqual(copied['filename'], 'old_v2.json')
        self.assertEqual((self.directory / 'old.json').read_bytes(), original)
        self.assertEqual(json.loads((self.directory / copied['filename']).read_text())['schema_version'], 2)
        again = self.store.save('old_v2.json', loaded['scenario'], 'duplicate')
        self.assertEqual(again['filename'], 'old_v3.json')

    def test_revision_conflict_preserves_bytes(self):
        first = self.store.save('line', legacy_scenario())
        changed = legacy_scenario()
        changed['notes']['owner'] = 'Changed'
        self.store.save('line', changed, 'overwrite', first['revision'])
        before = (self.directory / 'line.json').read_bytes()
        with self.assertRaises(ScenarioStorageError) as caught:
            self.store.save('line', legacy_scenario(), 'overwrite', first['revision'])
        self.assertEqual(caught.exception.status, 'conflict')
        self.assertEqual((self.directory / 'line.json').read_bytes(), before)

    def test_import_export_roundtrip_does_not_save(self):
        imported = self.client.post('/import-scenario', json={'scenario': legacy_scenario()})
        self.assertEqual(imported.status_code, 200)
        data = imported.get_json()
        self.assertEqual(data['migrated_from'], 1)
        exported = self.client.post('/export-scenario', json={'scenario': data['scenario'], 'filename': 'portable.json'})
        self.assertEqual(exported.status_code, 200)
        self.assertIn('portable.json', exported.headers['Content-Disposition'])
        self.assertEqual(exported.get_json(), data['scenario'])
        self.assertEqual(self.store.list_files(), [])
        saved = self.client.post('/save-scenario', json={'name': 'portable', 'scenario': exported.get_json()})
        self.assertEqual(saved.status_code, 200)
        loaded = self.client.get('/load-scenario/portable.json').get_json()
        self.assertEqual(loaded['scenario'], data['scenario'])
        self.assertIsNone(loaded['migrated_from'])

    def test_invalid_imports_return_400_and_create_no_files(self):
        current = validate_scenario(legacy_scenario())
        invalid = [None, [], {'schema_version': 3}, {**current, 'boxes': []}, {**current, 'notes': float('nan')}]
        for loc in [None, [], {}]:
            data = deepcopy(current)
            data['operators']['Op1']['sequence'][0]['loc'] = loc
            invalid.append(data)
        for color in ['blue', [999, 0, 0]]:
            data = deepcopy(current)
            data['operators']['Op1']['color'] = color
            invalid.append(data)
        for data in invalid:
            with self.subTest(data=data):
                response = self.client.post('/import-scenario', json={'scenario': data})
                self.assertEqual(response.status_code, 400)
                self.assertTrue(response.get_json()['errors'])
        self.assertEqual(self.store.list_files(), [])

    def test_unreadable_and_future_saved_files_return_clear_errors(self):
        (self.directory / 'broken.json').write_text('not json')
        (self.directory / 'future.json').write_text(json.dumps({'schema_version': 100}))
        self.assertEqual(self.client.get('/load-scenario/broken.json').status_code, 400)
        response = self.client.get('/load-scenario/future.json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('newer', response.get_json()['error'])

    def test_event_contract_and_module_entry_points(self):
        self.assertEqual(self.client.post('/launch', json=legacy_scenario()).status_code, 200)
        self.assertEqual(self.client.get('/events').get_json()['event_schema_version'], 1)
        for url, script in [('/builder', 'builder.js'), ('/simulate', 'playback.js')]:
            page = self.client.get(url).get_data(as_text=True)
            self.assertIn('type="module"', page)
            self.assertIn(script, page)
            self.assertNotIn('<script>', page)

    def test_dashboard_and_planned_modules_have_working_navigation(self):
        dashboard = self.client.get('/').get_data(as_text=True)
        self.assertIn('Your planning workspace', dashboard)
        self.assertIn('Open Line Builder', dashboard)
        self.assertNotIn('id="builder-canvas"', dashboard)
        self.assertEqual(self.client.get('/dashboard').status_code, 200)
        for path in ('/builder', '/pqpr', '/line-balancing'):
            self.assertIn(f'href="{path}"', dashboard)
            self.assertEqual(self.client.get(path).status_code, 200)
        builder = self.client.get('/builder').get_data(as_text=True)
        self.assertIn('id="builder-canvas"', builder)
        self.assertIn('aria-current="page"', builder)
        pqpr_page = self.client.get('/pqpr').get_data(as_text=True)
        self.assertIn('id="pqpr-app"', pqpr_page)
        balancing_page = self.client.get('/line-balancing').get_data(as_text=True)
        self.assertIn('id="balance-app"', balancing_page)
        self.assertNotIn('id="builder-canvas"', balancing_page)


if __name__ == '__main__':
    unittest.main()
