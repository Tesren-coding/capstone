"""Run with: python -m unittest discover -s tests -p test_rename_storage.py -v
Tests rename semantics for file and SQL storage without needing Flask/SQL Server.
"""
from pathlib import Path
import json
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scenario_store import ScenarioStore, ScenarioStorageError, revision
from scenario_schema import validate_scenario
from sqlserver_store import SqlServerStore
from test_sqlserver_storage import Connection


def draft():
    return {'schema_version': 2, 'takt_time': 30, 'stations': {}, 'operators': {}, 'boxes': {}}


class RenameStorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.sqlite = str(self.root / 'sqlmock.sqlite')
        self.stores = [
            ScenarioStore(self.root / 'scenarios'),
            SqlServerStore('scenario', lambda d: validate_scenario(d, require_runnable=False),
                           connection_string='fake', connect=lambda _: Connection(self.sqlite)),
        ]

    def tearDown(self):
        self.tmp.cleanup()

    def test_rename_preserves_original_document_and_revision(self):
        for store in self.stores:
            with self.subTest(storage=type(store).__name__):
                saved = store.save('N1', draft())
                before = store.load('N1')
                result = store.rename('N1.json', 'Line One', saved['revision'])
                self.assertEqual(result, {'status': 'renamed', 'filename': 'Line_One.json',
                                          'revision': saved['revision']})
                self.assertFalse(store.load('N1.json')['found'])
                after = store.load('Line_One.json')
                self.assertEqual(after['revision'], before['revision'])
                self.assertEqual(after['scenario'], before['scenario'])
                self.assertEqual(store.list_files(), ['Line_One.json'])
                unchanged = store.rename('Line One', 'Line_One.json', after['revision'])
                self.assertEqual(unchanged['revision'], before['revision'])

    def test_duplicate_missing_conflict_and_invalid_names_never_change_saved_data(self):
        for store in self.stores:
            with self.subTest(storage=type(store).__name__):
                a = store.save('source', draft())
                store.save('target', draft())
                for target, expected in [('target', 'exists'), ('', 'invalid'), ('x' * 300, 'invalid')]:
                    with self.assertRaises(ScenarioStorageError) as error:
                        store.rename('source', target, a['revision'])
                    self.assertEqual(error.exception.status, expected)
                with self.assertRaises(ScenarioStorageError) as error:
                    store.rename('source', 'renamed', 'stale-revision')
                self.assertEqual(error.exception.status, 'conflict')
                with self.assertRaises(ScenarioStorageError) as error:
                    store.rename('missing', 'renamed')
                self.assertEqual(error.exception.status, 'missing')
                self.assertEqual(store.list_files(), ['source.json', 'target.json'])
                self.assertEqual(store.load('source')['revision'], a['revision'])

    def test_sql_rename_leaves_raw_payload_and_dates_unchanged(self):
        store = self.stores[1]
        store.save('before', draft())
        with sqlite3.connect(self.sqlite) as db:
            old = db.execute('SELECT payload, revision, created_utc, modified_utc FROM CapstoneSaves '
                             'WHERE save_type = ? AND file_name = ?', ('scenario', 'before.json')).fetchone()
        store.rename('before', 'after')
        with sqlite3.connect(self.sqlite) as db:
            new = db.execute('SELECT payload, revision, created_utc, modified_utc FROM CapstoneSaves '
                             'WHERE save_type = ? AND file_name = ?', ('scenario', 'after.json')).fetchone()
        self.assertEqual(new, old)

    def test_file_rename_leaves_original_bytes_intact(self):
        store = self.stores[0]
        source = store.directory / 'legacy.json'
        source.parent.mkdir(parents=True, exist_ok=True)
        raw = b'{"takt_time":30,"stations":{},"operators":{},"boxes":{}}\n'
        source.write_bytes(raw)
        result = store.rename('legacy', 'new_legacy')
        self.assertEqual(result['revision'], revision(raw))
        self.assertFalse(source.exists())
        self.assertEqual((store.directory / 'new_legacy.json').read_bytes(), raw)


if __name__ == '__main__':
    unittest.main()
