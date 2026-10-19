"""One-time, repeatable JSON -> SQL Server migration (source files remain untouched).

Usage: python migrate_json_to_sqlserver.py --dry-run
       python migrate_json_to_sqlserver.py
       python migrate_json_to_sqlserver.py --overwrite  # explicit conflict replacement
Run with CAPSTONE_SQLSERVER_CONNECTION_STRING set (see Updates/SQLSERVER_SETUP.md).
"""
import argparse
import json
from pathlib import Path

from balancing_schema import validate_plan
from builder_setup import validate_setup
from pqpr_schema import validate_pqpr
from scenario_schema import validate_scenario
from sqlserver_store import SqlServerStore

ROOT = Path(__file__).resolve().parent
SOURCES = {
    'scenario': ('scenarios', lambda data: validate_scenario(data, require_runnable=False), 'scenario'),
    'pqpr': ('pqpr_projects', validate_pqpr, 'project'),
    'balancing': ('balancing_plans', validate_plan, 'plan'),
    'builder_setup': ('builder_setups', validate_setup, 'setup'),
}


def migrate(root=ROOT, dry_run=False, overwrite=False, writer=None, connect=None):
    output = writer or print
    totals = {'imported': 0, 'identical': 0, 'conflict': 0, 'replaced': 0, 'invalid': 0, 'ready': 0}
    for kind, (directory, normalizer, field) in SOURCES.items():
        source = Path(root) / directory
        files = sorted(source.glob('*.json')) if source.exists() else []
        output(f'{kind}: {len(files)} JSON file(s) in {source}')
        sql_store = None if dry_run else SqlServerStore(kind, normalizer, field, connect=connect)
        for path in files:
            try:
                raw = path.read_bytes()
                original = json.loads(raw)
                normalizer(original)
                if dry_run:
                    status = 'ready'
                else:
                    status = sql_store.import_original(path.name, original, raw, overwrite=overwrite)
            except Exception as exc:
                # This is a *file*-level failure. Preserve all sources for diagnosis.
                status = 'invalid'
                output(f'  {path.name}: ERROR ({type(exc).__name__}: {exc})')
            else:
                output(f'  {path.name}: {status}')
            totals[status] += 1
    output('Summary: ' + ', '.join(f'{key}={value}' for key, value in totals.items()))
    return totals


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='Validate JSON files without touching SQL Server')
    parser.add_argument('--overwrite', action='store_true', help='Replace conflicting SQL documents (not recommended)')
    parser.add_argument('--data-root', type=Path, default=ROOT, help='Folder containing the four JSON save folders')
    args = parser.parse_args()
    result = migrate(args.data_root, args.dry_run, args.overwrite)
    if result['invalid'] or result['conflict']:
        raise SystemExit(1)
