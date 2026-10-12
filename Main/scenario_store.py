"""JSON scenario persistence. Reads migrate in memory and never rewrite originals."""
import hashlib
import json
from pathlib import Path
import re
import tempfile
from threading import Lock

from scenario_schema import validate_scenario


class ScenarioStorageError(Exception):
    def __init__(self, status, message, code=400, **details):
        super().__init__(message)
        self.status, self.code, self.details = status, code, details


def safe_filename(name):
    name = re.sub(r'[^A-Za-z0-9_\- ]', '', name.strip()).replace(' ', '_')
    return name or 'untitled'


def file_stem(name):
    if not isinstance(name, str):
        raise ScenarioStorageError('invalid', 'Scenario name must be text.')
    return safe_filename(name[:-5] if name.lower().endswith('.json') else name)


def revision(raw):
    return hashlib.sha256(raw).hexdigest()


class ScenarioStore:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.lock = Lock()

    def list_files(self):
        with self.lock:
            self.directory.mkdir(parents=True, exist_ok=True)
            return sorted(p.name for p in self.directory.glob('*.json') if p.is_file())

    def load(self, name):
        filename = file_stem(name) + '.json'
        with self.lock:
            try:
                raw = (self.directory / filename).read_bytes()
            except FileNotFoundError:
                return {'found': False, 'scenario': None}
        try:
            original = json.loads(raw)
        except (ValueError, UnicodeDecodeError) as exc:
            raise ScenarioStorageError('invalid', 'Saved scenario is not valid JSON.') from exc
        scenario = validate_scenario(original, require_runnable=False)
        source_version = original.get('schema_version', 1)
        return {'found': True, 'filename': filename, 'scenario': scenario,
                'revision': revision(raw), 'migrated_from': source_version if source_version != scenario['schema_version'] else None}

    def save(self, name, scenario, mode='create', expected_revision=None):
        stem = file_stem(name)
        if mode not in ('create', 'duplicate', 'overwrite'):
            raise ScenarioStorageError('invalid', 'Unknown save mode.')
        scenario = validate_scenario(scenario, require_runnable=False)
        raw = (json.dumps(scenario, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
        with self.lock:
            self.directory.mkdir(parents=True, exist_ok=True)
            filename = stem + '.json'
            path = self.directory / filename
            if mode == 'duplicate':
                root = re.sub(r'_v[0-9]+$', '', stem)
                version = 2
                while True:
                    filename = f'{root}_v{version}.json'
                    path = self.directory / filename
                    try:
                        stream = path.open('xb')
                        break
                    except FileExistsError:
                        version += 1
            elif mode == 'create':
                try:
                    stream = path.open('xb')
                except FileExistsError as exc:
                    raise ScenarioStorageError('exists', 'A scenario with this name already exists.', 409, filename=filename) from exc
            else:
                try:
                    previous = path.read_bytes()
                except FileNotFoundError as exc:
                    raise ScenarioStorageError('missing', 'The original scenario no longer exists. Save a new version.', 409) from exc
                if expected_revision and expected_revision != revision(previous):
                    raise ScenarioStorageError('conflict', 'This scenario changed since you loaded it. Reload it or save a new version.', 409)
                temporary = None
                try:
                    with tempfile.NamedTemporaryFile(dir=self.directory, suffix='.tmp', delete=False) as stream:
                        temporary = Path(stream.name)
                        stream.write(raw)
                    temporary.replace(path)
                finally:
                    if temporary is not None:
                        temporary.unlink(missing_ok=True)
                return {'status': 'saved', 'filename': filename, 'revision': revision(raw)}
            try:
                with stream:
                    stream.write(raw)
            except Exception:
                path.unlink(missing_ok=True)
                raise
        return {'status': 'saved', 'filename': filename, 'revision': revision(raw)}

    def delete(self, name):
        with self.lock:
            try:
                (self.directory / (file_stem(name) + '.json')).unlink()
            except FileNotFoundError:
                return {'status': 'not_found'}
        return {'status': 'deleted'}
