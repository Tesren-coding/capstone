"""Balancing calculations, PQPR copy semantics and version-safe persistence."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as web
import balancing_routes as routes
from balancing_schema import blank_plan, plan_from_pqpr, validate_plan, analyse_plan
from balancing_store import BalancingStore
from scenario_schema import ScenarioValidationError
from scenario_store import ScenarioStorageError


def pqpr_project():
    return {'document_type': 'pqpr', 'schema_version': 1, 'project_name': 'N2 line',
            'processes': [{'id': 'p1', 'name': 'Inspect', 'category': 'in_line', 'manual_time': 4, 'auto_time': 2},
                          {'id': 'p2', 'name': 'Heat treat', 'category': 'out_of_line', 'manual_time': 6, 'auto_time': 20},
                          {'id': 'p3', 'name': 'Special repair', 'category': 'unique', 'manual_time': 3, 'auto_time': 0},
                          {'id': 'p4', 'name': 'Sometimes polish', 'category': 'in_line', 'manual_time': None, 'auto_time': None}],
            'framesizes': [{'id': 'f1', 'name': '7HA.01', 'stage': '2', 'component': 'Nozzle',
                           'applicability': {'p1': 'required', 'p2': 'required', 'p3': 'required', 'p4': 'optional'}},
                          {'id': 'f2', 'name': '9HA.02', 'applicability': {'p1': 'required'}}]}


def complete_plan():
    plan = plan_from_pqpr(pqpr_project(), 'f1')
    # Explicitly choose to represent each process as one working element.
    plan['steps'] = [dict(id=p['id'], balance_process_id=p['id'], process_id=p['pqpr_process_id'],
                         **{key:p[key] for key in ('name','category','applicability','included','manual_time','auto_time')},
                         value_class='unclassified') for p in plan['processes']]
    plan['takt_time'] = 5
    plan['steps'][3]['included'] = False
    plan['operators'] = [{'id': 'o1', 'name': 'Operator 1', 'sequence': ['p1']},
                         {'id': 'o2', 'name': 'Operator 2', 'sequence': ['p3']}]
    plan['next_operator_id'] = 3
    return plan


class BalancingTests(unittest.TestCase):
    def test_pqpr_copy_filters_route_and_does_not_mutate_source(self):
        original = pqpr_project()
        before = deepcopy(original)
        plan = plan_from_pqpr(original, 'f2', 'N2.json', 'revision')
        self.assertEqual([s['id'] for s in plan['processes']], ['p1'])
        self.assertEqual(plan['steps'], [])
        self.assertEqual(plan['source']['filename'], 'N2.json')
        plan['processes'][0]['manual_time'] = 8
        self.assertEqual(original, before)
        self.assertEqual(plan['source']['project']['processes'][0]['manual_time'], 4)
        self.assertEqual(validate_plan(plan), plan)
        with self.assertRaises(ScenarioValidationError):
            plan_from_pqpr(original, 'missing')

    def test_manual_workload_efficiency_and_automatic_time_are_separate(self):
        result = analyse_plan(complete_plan())
        self.assertEqual(result['active_steps'], 2)
        self.assertEqual(result['manual_total'], 7)
        self.assertEqual(result['operators'][0]['manual_time'], 4)
        self.assertEqual(result['operators'][0]['auto_time'], 2)
        self.assertEqual(result['operators'][0]['utilization'], 80)
        self.assertEqual(result['balance_efficiency'], 87.5)
        self.assertEqual(result['takt_load'], 70)
        self.assertEqual(result['minimum_operators'], 2)
        self.assertEqual(result['unassigned'], [])

    def test_optional_and_out_of_line_scope_changes(self):
        plan = complete_plan()
        plan['include_out_of_line'] = True
        plan['operators'][1]['sequence'].append('p2')
        result = analyse_plan(plan)
        self.assertEqual(result['manual_total'], 13)
        self.assertEqual(result['minimum_operators'], 3)
        self.assertEqual(result['operators'][1]['status'], 'over_takt')
        self.assertEqual(result['operators'][1]['auto_time'], 20)
        plan['steps'][3]['included'] = True
        result = analyse_plan(plan)
        self.assertEqual(result['unknown_manual'], ['p4'])
        self.assertIn('p4', result['unassigned'])
        self.assertIsNone(result['manual_total'])
        self.assertIsNone(result['balance_efficiency'])

    def test_blank_auto_counts_zero_without_blocking_manual_analysis(self):
        plan = complete_plan()
        plan['steps'][0]['auto_time'] = None
        result = analyse_plan(plan)
        self.assertEqual(result['balance_efficiency'], 87.5)
        self.assertEqual(result['operators'][0]['status'], 'within_takt')
        self.assertEqual(result['operators'][0]['auto_time'], 0)
        self.assertEqual(result['unknown_auto'], [])

    def test_over_takt_empty_operators_and_unassigned(self):
        plan = complete_plan()
        plan['operators'][0]['sequence'].append('p3')
        plan['operators'][1]['sequence'] = []
        result = analyse_plan(plan)
        self.assertEqual(result['operators'][0]['status'], 'over_takt')
        self.assertEqual(result['operators'][1]['status'], 'no_steps')
        self.assertEqual(result['balance_efficiency'], 50)
        plan['operators'][0]['sequence'] = ['p1']
        result = analyse_plan(plan)
        self.assertEqual(result['unassigned'], ['p3'])
        self.assertIsNone(result['balance_efficiency'])

    def test_unknown_manual_and_takt_do_not_claim_complete_workloads(self):
        plan = complete_plan()
        plan['steps'][2]['manual_time'] = None
        result = analyse_plan(plan)
        self.assertEqual(result['operators'][1]['status'], 'incomplete')
        self.assertEqual(result['operators'][1]['known_manual_time'], 0)
        self.assertIsNone(result['operators'][1]['utilization'])
        plan = complete_plan(); plan['takt_time'] = None
        self.assertEqual(analyse_plan(plan)['operators'][0]['status'], 'incomplete')
        self.assertIsNone(analyse_plan(plan)['minimum_operators'])
        validate_plan(plan)

    def test_decimal_rounding_does_not_add_a_spurious_operator(self):
        plan = complete_plan()
        plan['takt_time'] = 0.1
        plan['steps'][0]['manual_time'] = 0.1
        plan['steps'][2]['manual_time'] = 0.2
        self.assertEqual(analyse_plan(plan)['minimum_operators'], 3)
        plan['steps'][2]['manual_time'] = 0.20001
        self.assertEqual(analyse_plan(plan)['minimum_operators'], 4)
        plan['steps'][0]['manual_time'] = 1e-20
        plan['steps'][2]['manual_time'] = 0
        self.assertEqual(analyse_plan(plan)['minimum_operators'], 1)
        plan['steps'][0]['manual_time'] = 0
        self.assertEqual(analyse_plan(plan)['minimum_operators'], 0)

    def test_invalid_versions_references_and_duplicate_assignments(self):
        invalid = []
        for version in (4, 100, True, None, '1'):
            plan = complete_plan(); plan['schema_version'] = version; invalid.append(plan)
        plan = complete_plan(); plan['operators'][1]['sequence'].append('p1'); invalid.append(plan)
        plan = complete_plan(); plan['operators'][1]['sequence'].append('missing'); invalid.append(plan)
        plan = complete_plan(); plan['steps'][0]['included'] = False; invalid.append(plan)
        plan = complete_plan(); plan['schema_version'] = 1; plan['steps'].pop(); invalid.append(plan)
        plan = complete_plan(); plan['schema_version'] = 1; plan['steps'][0]['process_id'] = 'missing'; invalid.append(plan)
        plan = complete_plan(); plan['steps'][0]['manual_time'] = -1; invalid.append(plan)
        plan = complete_plan(); plan['steps'][0]['value_class'] = 'invalid'; invalid.append(plan)
        plan = complete_plan(); plan['takt_time'] = 0; invalid.append(plan)
        plan = complete_plan(); plan['source'] = None; invalid.append(plan)
        for plan in invalid:
            with self.subTest(plan=plan), self.assertRaises(ScenarioValidationError):
                validate_plan(plan)

    def test_standalone_processes_need_no_pqpr(self):
        plan = blank_plan()
        plan['processes'] = [deepcopy(complete_plan()['processes'][0])]
        step = deepcopy(complete_plan()['steps'][0])
        step.update(id='s1', process_id=None, name='Independent process')
        plan['steps'] = [step]
        plan['operators'] = [{'id': 'o1', 'name': 'Alice', 'sequence': ['s1']}]
        plan['next_step_id'] = 2
        self.assertEqual(validate_plan(plan), plan)
        self.assertEqual(analyse_plan(plan)['manual_total'], 4)
        plan['next_step_id'] = True
        with self.assertRaises(ScenarioValidationError): validate_plan(plan)

    def test_format_one_migrates_without_mutating_source_or_assignments(self):
        original = complete_plan(); original['schema_version'] = 1
        original.pop('next_step_id'); original['notes'] = {'owner': 'Example'}
        before = deepcopy(original)
        migrated = validate_plan(original)
        self.assertEqual(original, before)
        self.assertEqual(migrated['schema_version'], 3)
        self.assertEqual(migrated['operators'], before['operators'])
        self.assertEqual(migrated['source'], before['source'])
        self.assertEqual(migrated['notes'], before['notes'])
        self.assertEqual(migrated['next_step_id'], 1)

    def test_imported_origin_does_not_constrain_independent_process_edits(self):
        plan = complete_plan()
        plan['steps'] = plan['steps'][:3]
        plan['steps'][0]['applicability'] = 'optional'
        extra = deepcopy(plan['steps'][0]); extra.update(id='s1', process_id=None, name='Walking')
        plan['steps'].append(extra)
        plan['operators'][0]['sequence'].append('s1')
        self.assertEqual(validate_plan(plan), plan)
        self.assertEqual(plan['source']['project']['processes'][0]['name'], 'Inspect')

    def test_blank_plan_and_extra_metadata_roundtrip(self):
        plan = blank_plan(); plan['notes'] = {'owner': 'Example'}
        self.assertEqual(validate_plan(plan), plan)
        self.assertIsNone(analyse_plan(plan)['balance_efficiency'])


class BalancingRoutesTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.previous = routes.balancing_store
        self.store = BalancingStore(self.temporary.name)
        routes.balancing_store = self.store
        self.client = web.app.test_client()

    def tearDown(self):
        routes.balancing_store = self.previous
        self.temporary.cleanup()

    def test_save_load_duplicate_revision_and_original_preserved(self):
        first = self.client.post('/line-balancing/api/save', json={'plan': complete_plan(), 'name': 'balance'}).get_json()
        loaded = self.client.get('/line-balancing/api/plans/balance.json').get_json()
        self.assertEqual(loaded['plan'], complete_plan())
        self.assertEqual(first['revision'], loaded['revision'])
        original = Path(self.temporary.name, 'balance.json').read_bytes()
        self.assertEqual(self.store.save('balance', complete_plan(), 'duplicate')['filename'], 'balance_v2.json')
        self.assertEqual(Path(self.temporary.name, 'balance.json').read_bytes(), original)
        plan = complete_plan(); plan['takt_time'] = 10
        self.store.save('balance', plan, 'overwrite', first['revision'])
        with self.assertRaises(ScenarioStorageError):
            self.store.save('balance', complete_plan(), 'overwrite', first['revision'])

    def test_loading_old_plan_does_not_rewrite_original_file(self):
        original = complete_plan(); original['schema_version'] = 1; original.pop('next_step_id')
        target = Path(self.temporary.name, 'old.json')
        target.write_text(json.dumps(original))
        before = target.read_bytes()
        loaded = self.store.load('old.json')
        self.assertEqual(loaded['plan']['schema_version'], 3)
        self.assertEqual(target.read_bytes(), before)
        self.store.save('old', loaded['plan'], 'duplicate')
        self.assertEqual(target.read_bytes(), before)
        self.assertEqual(self.store.load('old_v2.json')['plan']['schema_version'], 3)

    def test_source_import_export_and_analysis_do_not_save(self):
        result = self.client.post('/line-balancing/api/from-pqpr', json={'project': pqpr_project(), 'framesize_id': 'f1'})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(result.get_json()['plan']['processes']), 4)
        self.assertEqual(result.get_json()['plan']['steps'], [])
        plan = complete_plan()
        imported = self.client.post('/line-balancing/api/import', json={'plan': plan}).get_json()
        exported = self.client.post('/line-balancing/api/export', json={'plan': imported['plan']})
        self.assertEqual(exported.get_json(), plan)
        analysis = self.client.post('/line-balancing/api/analyse', json={'plan': plan}).get_json()['analysis']
        self.assertEqual(analysis, analyse_plan(plan))
        self.assertEqual(self.store.list_files(), [])

    def test_dashboard_and_editor_available_and_future_import_rejected(self):
        dashboard = self.client.get('/').get_data(as_text=True)
        self.assertIn('Open Line Balancing', dashboard)
        self.assertNotIn('module-status--planned', dashboard)
        page = self.client.get('/line-balancing').get_data(as_text=True)
        self.assertIn('id="balance-app"', page)
        self.assertIn('balancing.js', page)
        self.assertNotIn('<script>', page)
        plan = complete_plan(); plan['schema_version'] = 99
        response = self.client.post('/line-balancing/api/import', json={'plan': plan})
        self.assertEqual(response.status_code, 400)
        self.assertIn('newer', response.get_json()['error'])
