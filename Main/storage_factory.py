"""Select JSON files (legacy/testing) or SQL Server for ALL four save modules."""
import os
from pathlib import Path

from sqlserver_store import SqlServerStore


def make_store(kind, directory, legacy_type, normalizer, field_name):
    backend = os.environ.get('CAPSTONE_STORAGE_BACKEND', 'json').strip().lower()
    if backend == 'json':
        # Keep old JSON saves usable after unpacking a new project ZIP.
        # By default, they live next to the running app.py (NOT next to
        # the PowerShell working directory or beside a previous ZIP).
        # An explicitly configured path can point at a pre-existing folder.
        if kind == 'scenario':
            override = os.environ.get('CAPSTONE_SCENARIOS_DIR', '').strip()
            if override:
                directory = Path(override).expanduser().resolve()
            print(f'[Capstone] JSON scenarios folder: {Path(directory).resolve()}', flush=True)
        return legacy_type(directory)
    if backend == 'sqlserver':
        return SqlServerStore(kind, normalizer, field_name)
    raise RuntimeError('CAPSTONE_STORAGE_BACKEND must be json or sqlserver.')
