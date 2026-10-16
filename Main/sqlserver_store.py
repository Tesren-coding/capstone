"""SQL Server Express persistence, preserving the existing JSON-based API contracts.

One relational row represents one saved document. Its variable/nested document is
kept as NVARCHAR(MAX) JSON; the save *itself* lives in SQL Server, not on disk.
This lets existing clients and old scenario formats keep working unchanged.
"""
import hashlib
import json
import os
import re
from threading import Lock

from scenario_store import ScenarioStorageError, file_stem

_GLOBAL_SCHEMA_LOCK = Lock()  # Avoid simultaneous first-use DDL across module stores.

TABLE_SQL = """
IF OBJECT_ID(N'dbo.CapstoneSaves', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.CapstoneSaves (
        save_type NVARCHAR(32) NOT NULL,
        file_name NVARCHAR(255) NOT NULL,
        payload NVARCHAR(MAX) NOT NULL,
        revision CHAR(64) NOT NULL,
        created_utc DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
        modified_utc DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
        CONSTRAINT PK_CapstoneSaves PRIMARY KEY (save_type, file_name),
        CONSTRAINT CK_CapstoneSaves_ValidJSON CHECK (ISJSON(payload) = 1)
    );
END
"""

_SELECT_REVISION = 'SELECT revision FROM dbo.CapstoneSaves WHERE save_type = ? AND file_name = ?'
_INSERT = 'INSERT INTO dbo.CapstoneSaves (save_type, file_name, payload, revision) VALUES (?, ?, ?, ?)'
_UPDATE = ('UPDATE dbo.CapstoneSaves SET payload = ?, revision = ?, modified_utc = SYSUTCDATETIME() '
           'WHERE save_type = ? AND file_name = ?')


def _raw_json(document):
    return (json.dumps(document, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')


def _revision(raw):
    return hashlib.sha256(raw).hexdigest()


def _is_duplicate_error(exc):
    # SQL Server unique-key errors: native error codes 2601 / 2627; ODBC SQLSTATE 23000.
    args = getattr(exc, 'args', ())
    return any('23000' in str(x) or '2601' in str(x) or '2627' in str(x) for x in args)


class SqlServerStore:
    """Drop-in replacement for the four file-backed store variants.

    `kind` isolates scenario, PQPR, balancing and builder setup names, so identical
    filenames in separate modules never collide. A new connection per operation is
    safe for concurrent Flask requests; SQL transactions enforce atomic writes.
    """

    def __init__(self, kind, normalizer, field_name='scenario', connection_string=None, connect=None):
        if kind not in ('scenario', 'pqpr', 'balancing', 'builder_setup'):
            raise ValueError('Unknown saved-document kind')
        self.kind = kind
        self.normalizer = normalizer
        self.field_name = field_name
        self.connection_string = connection_string or os.environ.get('CAPSTONE_SQLSERVER_CONNECTION_STRING', '')
        if not self.connection_string and connect is None:
            raise RuntimeError('Set CAPSTONE_SQLSERVER_CONNECTION_STRING to connect to SQL Server Express.')
        self._connect_override = connect
        self._schema_ready = False
        self._schema_lock = _GLOBAL_SCHEMA_LOCK

    def _connect(self):
        if self._connect_override is not None:
            return self._connect_override(self.connection_string)
        try:
            import pyodbc
        except ImportError as exc:
            raise RuntimeError('SQL storage needs pyodbc. Run: python -m pip install pyodbc') from exc
        # ODBC driver's login timeout protects endpoints when the instance is down.
        return pyodbc.connect(self.connection_string, autocommit=False, timeout=10)

    def _ready(self):
        if self._schema_ready:
            return
        with self._schema_lock:
            if self._schema_ready:
                return
            connection = self._connect()
            try:
                connection.cursor().execute(TABLE_SQL)
                connection.commit()
                self._schema_ready = True
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()

    def _operate(self, operation):
        self._ready()
        connection = self._connect()
        try:
            result = operation(connection.cursor())
            connection.commit()
            return result
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def list_files(self):
        def task(cursor):
            rows = cursor.execute('SELECT file_name FROM dbo.CapstoneSaves WHERE save_type = ? '
                                  'ORDER BY file_name', self.kind).fetchall()
            return [row[0] for row in rows]
        return self._operate(task)

    def load(self, name):
        filename = file_stem(name) + '.json'
        def task(cursor):
            return cursor.execute('SELECT payload, revision FROM dbo.CapstoneSaves '
                                  'WHERE save_type = ? AND file_name = ?', self.kind, filename).fetchone()
        row = self._operate(task)
        if row is None:
            return {'found': False, self.field_name: None}
        try:
            original = json.loads(row[0])
        except (ValueError, TypeError) as exc:
            raise ScenarioStorageError('invalid', 'Saved document is not valid JSON.') from exc
        document = self.normalizer(original)
        source_version = original.get('schema_version', 1)
        return {'found': True, 'filename': filename, self.field_name: document,
                'revision': row[1].strip(),
                'migrated_from': source_version if source_version != document['schema_version'] else None}

    def save(self, name, document, mode='create', expected_revision=None):
        stem = file_stem(name)
        if mode not in ('create', 'duplicate', 'overwrite'):
            raise ScenarioStorageError('invalid', 'Unknown save mode.')
        document = self.normalizer(document)
        raw = _raw_json(document)
        payload = raw.decode('utf-8')
        new_revision = _revision(raw)
        filename = stem + '.json'

        def task(cursor):
            if mode == 'duplicate':
                root = re.sub(r'_v[0-9]+$', '', stem)
                for version in range(2, 100002):
                    candidate = f'{root}_v{version}.json'
                    try:
                        cursor.execute(_INSERT, self.kind, candidate, payload, new_revision)
                        return candidate
                    except Exception as exc:
                        if not _is_duplicate_error(exc):
                            raise
                raise ScenarioStorageError('conflict', 'Too many versions of this document.', 409)
            if mode == 'create':
                try:
                    cursor.execute(_INSERT, self.kind, filename, payload, new_revision)
                except Exception as exc:
                    if _is_duplicate_error(exc):
                        raise ScenarioStorageError('exists', 'A document with this name already exists.',
                                                   409, filename=filename) from exc
                    raise
                return filename
            # Both existence and optimistic-concurrency check happen in the database.
            if expected_revision:
                cursor.execute(_UPDATE + ' AND revision = ?', payload, new_revision,
                               self.kind, filename, expected_revision)
            else:
                cursor.execute(_UPDATE, payload, new_revision, self.kind, filename)
            if cursor.rowcount != 1:
                exists = cursor.execute(_SELECT_REVISION, self.kind, filename).fetchone()
                if exists is None:
                    raise ScenarioStorageError('missing', 'The original document no longer exists. Save a new version.', 409)
                raise ScenarioStorageError('conflict', 'This document changed since you loaded it. Reload it or save a new version.', 409)
            return filename

        saved_name = self._operate(task)
        return {'status': 'saved', 'filename': saved_name, 'revision': new_revision}

    def delete(self, name):
        filename = file_stem(name) + '.json'
        def task(cursor):
            cursor.execute('DELETE FROM dbo.CapstoneSaves WHERE save_type = ? AND file_name = ?',
                           self.kind, filename)
            return cursor.rowcount
        return {'status': 'deleted' if self._operate(task) else 'not_found'}

    def import_original(self, name, original, original_bytes, overwrite=False):
        """Migrate a file without normalizing/reformatting it or changing its revision.

        The original payload is preserved, while *load()* still does its in-memory
        upgrade for legacy versions. Existing SQL saves are never changed by default.
        """
        filename = file_stem(name) + '.json'
        self.normalizer(original)  # Reject incompatible/corrupt files before writing.
        try:
            raw = original_bytes.decode('utf-8-sig')
        except UnicodeDecodeError:
            # json.loads(bytes) also supports UTF-16/32. SQL stores Unicode text.
            raw = json.dumps(original, ensure_ascii=False, allow_nan=False)
        revision = _revision(original_bytes)
        def task(cursor):
            old = cursor.execute(_SELECT_REVISION, self.kind, filename).fetchone()
            if old is not None:
                if old[0].strip() == revision:
                    return 'identical'
                if not overwrite:
                    return 'conflict'
                cursor.execute(_UPDATE, raw, revision, self.kind, filename)
                return 'replaced'
            try:
                cursor.execute(_INSERT, self.kind, filename, raw, revision)
                return 'imported'
            except Exception as exc:
                if _is_duplicate_error(exc):
                    return 'conflict'  # Competing insert: do not modify it.
                raise
        return self._operate(task)
