"""PQPR validation, timing and file compatibility tests."""
from copy import deepcopy
from io import BytesIO
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as web
import pqpr_routes as routes
from pqpr_excel import worksheets, import_worksheet
from pqpr_schema import validate_pqpr, frame_totals
from pqpr_store import PQPRStore
from scenario_schema import ScenarioValidationError
from scenario_store import ScenarioStorageError


def project():
    return {'document_type': 'pqpr', 'schema_version': 1, 'project_name': 'N2 line',
            'processes': [{'id': 'p1', 'name': 'Inspect', 'category': 'in_line', 'manual_time': .5, 'auto_time': 0},
                          {'id': 'p2', 'name': 'Heat treat', 'category': 'out_of_line', 'manual_time': 1, 'auto_time': 20},
                          {'id': 'p3', 'name': 'Unique repair', 'category': 'unique', 'manual_time': None, 'auto_time': None}],
            'framesizes': [{'id': 'f1', 'name': '7HA.01', 'stage': '2', 'component': 'Nozzle', 'applicability': {'p1': 'required', 'p2': 'optional'}},
                           {'id': 'f2', 'name': '9HA.02', 'applicability': {'p1': 'required', 'p3': 'required'}}],
            'notes': {'owner': 'Example'}}


class PQPRTests(unittest.TestCase):
    def test_validation_preserves_input_and_extra_fields(self):
        original = project()
        before = deepcopy(original)
        result = validate_pqpr(original)
        self.assertEqual(original, before)
        self.assertEqual(result['notes'], before['notes'])
        self.assertEqual(result['framesizes'][1]['stage'], '')
        self.assertEqual(validate_pqpr(result), result)

    def test_unknown_manual_stays_unknown_and_blank_auto_defaults_zero(self):
        data = validate_pqpr(project())
        self.assertEqual(frame_totals(data, data['framesizes'][0]),
                         {'process_count': 2, 'optional_count': 1, 'manual_time': 1.5, 'auto_time': 20})
        unknown = frame_totals(data, data['framesizes'][1])
        self.assertIsNone(unknown['manual_time'])
        self.assertEqual(unknown['auto_time'], 0)
        data['framesizes'][1]['applicability'] = {}
        self.assertEqual(frame_totals(data, data['framesizes'][1])['manual_time'], 0)

    def test_reordering_does_not_change_route_membership_or_totals(self):
        data = validate_pqpr(project())
        expected = [frame_totals(data, f) for f in data['framesizes']]
        data['processes'].reverse()
        self.assertEqual([frame_totals(data, f) for f in data['framesizes']], expected)

    def test_invalid_references_categories_times_and_versions(self):
        cases = []
        for version in (2, 99, None, True, '1'):
            cases.append({**project(), 'schema_version': version})
        for time in (-1, True, '2', float('inf')):
            data = project(); data['processes'][0]['manual_time'] = time; cases.append(data)
        data = project(); data['framesizes'][0]['applicability']['missing'] = 'required'; cases.append(data)
        data = project(); data['framesizes'][0]['applicability']['p1'] = 'bad'; cases.append(data)
        data = project(); data['processes'][0]['category'] = 'red'; cases.append(data)
        data = project(); data['processes'][1]['id'] = 'p1'; cases.append(data)
        data = project(); data['framesizes'][0]['id'] = '__proto__'; cases.append(data)
        cases += [None, [], {'schema_version': 2, 'stations': {}}]
        for data in cases:
            with self.subTest(data=data), self.assertRaises(ScenarioValidationError):
                validate_pqpr(data)

    def test_empty_draft_is_valid(self):
        validate_pqpr({'document_type': 'pqpr', 'schema_version': 1, 'project_name': 'Draft', 'processes': [], 'framesizes': []})


class PQPRRouteTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.store = PQPRStore(self.temporary.name)
        self.previous = routes.pqpr_store
        routes.pqpr_store = self.store
        self.client = web.app.test_client()

    def tearDown(self):
        routes.pqpr_store = self.previous
        self.temporary.cleanup()

    def test_save_load_duplicate_and_revision_conflict(self):
        first = self.client.post('/pqpr/api/save', json={'project': project(), 'name': 'N2'}).get_json()
        loaded = self.client.get('/pqpr/api/projects/N2.json').get_json()
        self.assertEqual(loaded['project'], validate_pqpr(project()))
        self.assertEqual(loaded['revision'], first['revision'])
        copy = self.store.save('N2.json', project(), 'duplicate')
        self.assertEqual(copy['filename'], 'N2_v2.json')
        changed = project(); changed['project_name'] = 'Changed'
        self.store.save('N2', changed, 'overwrite', first['revision'])
        with self.assertRaises(ScenarioStorageError):
            self.store.save('N2', project(), 'overwrite', first['revision'])
        self.assertEqual(self.store.load('N2')['project']['project_name'], 'Changed')

    def test_import_export_does_not_save_or_accept_scenarios(self):
        imported = self.client.post('/pqpr/api/import', json={'project': project()})
        self.assertEqual(imported.status_code, 200)
        exported = self.client.post('/pqpr/api/export', json={'project': imported.get_json()['project']})
        self.assertEqual(exported.get_json(), imported.get_json()['project'])
        self.assertEqual(self.store.list_files(), [])
        self.assertEqual(self.client.post('/pqpr/api/import', json={'project': {'schema_version': 2, 'stations': {}}}).status_code, 400)

    def test_saved_future_format_and_invalid_excel_return_400(self):
        future = project(); future['schema_version'] = 3
        Path(self.temporary.name, 'future.json').write_text(json.dumps(future))
        result = self.client.get('/pqpr/api/projects/future.json')
        self.assertEqual(result.status_code, 400)
        self.assertIn('newer', result.get_json()['error'])
        result = self.client.post('/pqpr/api/import-excel', data={'file': (BytesIO(b'not an excel workbook'), 'bad.xlsx')})
        self.assertEqual(result.status_code, 400)

    def test_dashboard_marks_pqpr_available(self):
        dashboard = self.client.get('/').get_data(as_text=True)
        self.assertIn('Open PQPR', dashboard)
        self.assertIn('href="/pqpr"', dashboard)
        page = self.client.get('/pqpr').get_data(as_text=True)
        self.assertIn('id="pqpr-matrix"', page)
        self.assertIn('pqpr.js', page)
        self.assertNotIn('<script>', page)


@unittest.skipUnless(os.environ.get('PQPR_REFERENCE_XLSX'), 'Set PQPR_REFERENCE_XLSX to test the reference workbook.')
class ReferenceWorkbookTests(unittest.TestCase):
    def test_both_reference_worksheets(self):
        raw = Path(os.environ['PQPR_REFERENCE_XLSX']).read_bytes()
        self.assertEqual([s['name'] for s in worksheets(raw)], ['PQPR (CS)', 'PQPR (FS)'])
        for sheet in ('PQPR (CS)', 'PQPR (FS)'):
            data, warnings = import_worksheet(raw, sheet, 'reference.xlsx')
            self.assertEqual(len(data['processes']), 63 if sheet == 'PQPR (CS)' else 61)
            self.assertEqual(len(data['framesizes']), 5)
            self.assertTrue(all(p['manual_time'] is None and p['auto_time'] == 0 for p in data['processes']))
            self.assertEqual(sum(p['category'] == 'unique' for p in data['processes']), 2)
            self.assertTrue(any('Unrecognized' in text for text in warnings))
            self.assertTrue(any(status == 'optional' for f in data['framesizes'] for status in f['applicability'].values()))


if __name__ == '__main__':
    unittest.main()
