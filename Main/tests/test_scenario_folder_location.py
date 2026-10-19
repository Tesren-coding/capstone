"""Existing user JSON saves are read from the configured folder without migration."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from scenario_store import ScenarioStore
from storage_factory import make_store


class ScenarioFolderTests(TestCase):
    def test_explicit_directory_uses_existing_saved_files(self):
        with TemporaryDirectory() as base:
            root = Path(base)
            old = root / 'prior-version' / 'scenarios'
            old.mkdir(parents=True)
            saved = old / 'N1.json'
            original = b'{"not_migrated": true}\n'
            saved.write_bytes(original)
            current = root / 'new-version' / 'scenarios'
            with patch.dict('os.environ', {
                'CAPSTONE_STORAGE_BACKEND': 'json',
                'CAPSTONE_SCENARIOS_DIR': str(old),
            }):
                store = make_store('scenario', current, ScenarioStore, None, 'scenario')
                self.assertEqual(store.list_files(), ['N1.json'])
                self.assertEqual(store.directory, old)
            self.assertEqual(saved.read_bytes(), original)
            self.assertFalse(current.exists())

    def test_default_directory_remains_project_local(self):
        with TemporaryDirectory() as base:
            current = Path(base) / 'scenarios'
            with patch.dict('os.environ', {'CAPSTONE_STORAGE_BACKEND': 'json'}, clear=True):
                store = make_store('scenario', current, ScenarioStore, None, 'scenario')
                self.assertEqual(store.directory, current)
                self.assertEqual(store.list_files(), [])
                self.assertTrue(current.is_dir())
