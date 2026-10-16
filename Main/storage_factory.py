"""Select JSON files (legacy/testing) or SQL Server for ALL four save modules."""
import os

from sqlserver_store import SqlServerStore


def make_store(kind, directory, legacy_type, normalizer, field_name):
    backend = os.environ.get('CAPSTONE_STORAGE_BACKEND', 'json').strip().lower()
    if backend == 'json':
        return legacy_type(directory)
    if backend == 'sqlserver':
        return SqlServerStore(kind, normalizer, field_name)
    raise RuntimeError('CAPSTONE_STORAGE_BACKEND must be json or sqlserver.')
