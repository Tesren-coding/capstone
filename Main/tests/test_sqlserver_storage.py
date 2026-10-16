"""SQL persistence contract tests using SQLite as a lightweight DB protocol fake.

These are useful without a SQL Server installation; actual ODBC/SQL Server tests
still need to be run on the Windows machine hosting the database.
"""
import json
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from balancing_schema import blank_plan, validate_plan
from builder_setup import setup_from_plan, validate_setup
from migrate_json_to_sqlserver import migrate
from pqpr_schema import validate_pqpr
from scenario_schema import validate_scenario
from scenario_store import ScenarioStorageError
from sqlserver_store import SqlServerStore


class SqlDuplicate(Exception):
    def __init__(self):
        super().__init__('23000', 'Violation of UNIQUE KEY constraint (2627)')


class Cursor:
    def __init__(self, connection):
        self.real = connection.cursor()
        self.rowcount = -1

    def execute(self, sql, *params):
        if 'IF OBJECT_ID(' in sql:
            sql = '''CREATE TABLE IF NOT EXISTS CapstoneSaves (
                save_type TEXT NOT NULL, file_name TEXT NOT NULL,
                payload TEXT NOT NULL, revision TEXT NOT NULL,
                created_utc TEXT DEFAULT CURRENT_TIMESTAMP,
                modified_utc TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (save_type, file_name))'''
        else:
            sql = sql.replace('dbo.CapstoneSaves', 'CapstoneSaves')
            sql = sql.replace('SYSUTCDATETIME()', 'CURRENT_TIMESTAMP')
        try:
            self.real.execute(sql, params)
        except sqlite3.IntegrityError as exc:
            raise SqlDuplicate() from exc
        self.rowcount = self.real.rowcount
        return self

    def fetchone(self): return self.real.fetchone()
    def fetchall(self): return self.real.fetchall()


class Connection:
    def __init__(self, filename): self.raw = sqlite3.connect(filename)
    def cursor(self): return Cursor(self.raw)
    def commit(self): self.raw.commit()
    def rollback(self): self.raw.rollback()
    def close(self): self.raw.close()


def example_scenario():
    return {'schema_version': 2, 'takt_time': 30, 'stations': {}, 'operators': {}, 'boxes': {}}


def example_pqpr():
    return {'document_type': 'pqpr', 'schema_version': 1, 'project_name': 'Line A',
            'processes': [], 'framesizes': []}


class SqlPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / 'fake_server.sqlite')
        self.connect = lambda _: Connection(self.db)
        self.scenario = self.store('scenario', lambda d: validate_scenario(d, require_runnable=False))

    def tearDown(self): self.tmp.cleanup()

    def store(self, kind, normalizer, field='scenario'):
        return SqlServerStore(kind, normalizer, field,
                              connection_string='fake sql connection', connect=self.connect)

    def test_create_list_load_duplicate_overwrite_and_delete(self):
        one = self.scenario.save('production line', example_scenario())
        self.assertEqual(one['filename'], 'production_line.json')
        self.assertEqual(self.scenario.list_files(), ['production_line.json'])
        loaded = self.scenario.load('production_line.json')
        self.assertEqual(loaded['scenario'], validate_scenario(example_scenario(), require_runnable=False))
        self.assertEqual(loaded['revision'], one['revision'])
        with self.assertRaises(ScenarioStorageError) as error:
            self.scenario.save('production line', example_scenario())
        self.assertEqual(error.exception.code, 409)
        self.assertEqual(self.scenario.save('production line', example_scenario(), 'duplicate')['filename'],
                         'production_line_v2.json')
        self.assertEqual(self.scenario.save('production_line_v2', example_scenario(), 'duplicate')['filename'],
                         'production_line_v3.json')
        changed = example_scenario(); changed['takt_time'] = 21
        current = self.scenario.save('production line', changed, 'overwrite', one['revision'])
        self.assertNotEqual(current['revision'], one['revision'])
        with self.assertRaises(ScenarioStorageError) as stale:
            self.scenario.save('production line', changed, 'overwrite', one['revision'])
        self.assertEqual(stale.exception.status, 'conflict')
        with self.assertRaises(ScenarioStorageError) as missing:
            self.scenario.save('missing', changed, 'overwrite')
        self.assertEqual(missing.exception.status, 'missing')
        self.assertEqual(self.scenario.delete('production_line'), {'status': 'deleted'})
        self.assertEqual(self.scenario.delete('production_line'), {'status': 'not_found'})
        self.assertFalse(self.scenario.load('production_line')['found'])

    def test_all_four_module_types_independently_usable(self):
        plan = blank_plan()
        documents = [
            ('scenario', lambda d: validate_scenario(d, require_runnable=False), 'scenario', example_scenario()),
            ('pqpr', validate_pqpr, 'project', example_pqpr()),
            ('balancing', validate_plan, 'plan', plan),
            ('builder_setup', validate_setup, 'setup', setup_from_plan(plan)),
        ]
        for kind, normalizer, field, obj in documents:
            with self.subTest(kind=kind):
                store = self.store(kind, normalizer, field)
                store.save('shared', obj)
                self.assertEqual(store.list_files(), ['shared.json'])
                self.assertEqual(store.load('shared')[field], normalizer(obj))
        self.assertEqual(self.scenario.list_files(), ['shared.json'])

    def test_migration_dry_run_and_non_destructive_repeat(self):
        root = Path(self.tmp.name)
        for source_name, document in (('scenarios', example_scenario()), ('pqpr_projects', example_pqpr()),
                                      ('balancing_plans', blank_plan()),
                                      ('builder_setups', setup_from_plan(blank_plan()))):
            (root / source_name).mkdir()
            (root / source_name / 'Example.json').write_text(json.dumps(document, ensure_ascii=False), encoding='utf8')
        messages = []
        dry = migrate(root, dry_run=True, writer=messages.append)
        self.assertEqual(dry['ready'], 4)
        self.assertFalse(Path(self.db).exists())
        first = migrate(root, connect=self.connect, writer=messages.append)
        self.assertEqual(first['imported'], 4)
        second = migrate(root, connect=self.connect, writer=messages.append)
        self.assertEqual(second['identical'], 4)
        changed = self.scenario.load('Example.json')['scenario']
        changed['takt_time'] = 17
        self.scenario.save('Example', changed, 'overwrite', self.scenario.load('Example')['revision'])
        conflict = migrate(root, connect=self.connect, writer=messages.append)
        self.assertEqual(conflict['conflict'], 1)
        self.assertEqual(self.scenario.load('Example')['scenario']['takt_time'], 17)
        replacement = migrate(root, overwrite=True, connect=self.connect, writer=messages.append)
        self.assertEqual(replacement['replaced'], 1)
        self.assertEqual(self.scenario.load('Example')['scenario']['takt_time'], 30)
        self.assertTrue((root / 'scenarios' / 'Example.json').exists())

    def test_migration_retains_old_revision_and_upgrades_only_in_memory(self):
        legacy = {'takt_time': 30, 'stations': {}, 'operators': {}, 'boxes': {}}
        original_bytes = json.dumps(legacy).encode('utf-8')
        store = self.scenario
        self.assertEqual(store.import_original('legacy.json', legacy, original_bytes), 'imported')
        loaded = store.load('legacy')
        self.assertEqual(loaded['migrated_from'], 1)
        self.assertEqual(loaded['scenario']['schema_version'], 2)
        self.assertEqual(loaded['revision'], __import__('hashlib').sha256(original_bytes).hexdigest())
        self.assertEqual(store.import_original('legacy', legacy, original_bytes), 'identical')

    def test_utf16_legacy_file_still_imports_without_renumbering_revision(self):
        legacy = {'takt_time': 30, 'stations': {}, 'operators': {}, 'boxes': {}}
        original_bytes = json.dumps(legacy).encode('utf-16')
        self.assertEqual(self.scenario.import_original('wide.json', legacy, original_bytes), 'imported')
        self.assertEqual(self.scenario.load('wide')['migrated_from'], 1)
        self.assertEqual(self.scenario.load('wide')['revision'],
                         __import__('hashlib').sha256(original_bytes).hexdigest())

    def test_invalid_files_are_not_imported(self):
        root = Path(self.tmp.name)
        (root/'scenarios').mkdir()
        (root/'scenarios'/'broken.json').write_text('{not-json}')
        result = migrate(root, connect=self.connect, writer=lambda _: None)
        self.assertEqual(result['invalid'], 1)
        self.assertEqual(self.scenario.list_files(), [])


if __name__ == '__main__': unittest.main()
