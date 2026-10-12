"""Version 1 PQPR project contract. Timings are shared per process, in minutes."""
from copy import deepcopy
import json
import math
import re
from scenario_schema import ScenarioValidationError

PQPR_SCHEMA_VERSION = 1
CATEGORIES = ('in_line', 'out_of_line', 'unique')


def validate_pqpr(original):
    if not isinstance(original, dict) or original.get('document_type') != 'pqpr':
        raise ScenarioValidationError(['Choose a PQPR project JSON file, not a line-builder scenario.'])
    version = original.get('schema_version')
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ScenarioValidationError(['PQPR schema_version must be a positive integer.'])
    if version > PQPR_SCHEMA_VERSION:
        raise ScenarioValidationError([f'PQPR format v{version} is newer than this app supports (v{PQPR_SCHEMA_VERSION}). Update the app to import it.'])
    data = deepcopy(original)
    errors = []
    try:
        json.dumps(data, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ScenarioValidationError(['PQPR data must contain valid JSON values and finite numbers.']) from exc
    if not isinstance(data.get('project_name'), str) or not data['project_name'].strip():
        errors.append('Name the project before saving or exporting.')
    for key in ('processes', 'framesizes'):
        if not isinstance(data.get(key), list):
            errors.append(f'{key} must be a list.')
    if errors:
        raise ScenarioValidationError(errors)

    def check_id(item, seen, label):
        identifier = item.get('id')
        if (not isinstance(identifier, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', identifier)
                or identifier in ('__proto__', 'constructor', 'prototype') or identifier in seen):
            errors.append(f'{label}: use a unique stable ID starting with a letter.')
        else:
            seen.add(identifier)

    process_ids = set()
    for index, process in enumerate(data['processes']):
        label = f'Process {index + 1}'
        if not isinstance(process, dict):
            errors.append(f'{label} must be an object.')
            continue
        check_id(process, process_ids, label)
        if not isinstance(process.get('name'), str) or not process['name'].strip():
            errors.append(f'{label} needs a name.')
        if process.get('category') not in CATEGORIES:
            errors.append(f'{label}: choose in line, out of line, or low hit rate / unique.')
        for key in ('manual_time', 'auto_time'):
            value = process.get(key)
            if key not in process or (value is not None and
                    (not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0)):
                errors.append(f'{label}: {key} must be a nonnegative number of minutes or null when unknown.')
    frame_ids = set()
    for index, frame in enumerate(data['framesizes']):
        label = f'Framesize {index + 1}'
        if not isinstance(frame, dict):
            errors.append(f'{label} must be an object.')
            continue
        check_id(frame, frame_ids, label)
        if not isinstance(frame.get('name'), str) or not frame['name'].strip():
            errors.append(f'{label} needs a name.')
        for key in ('stage', 'component'):
            frame.setdefault(key, '')
            if not isinstance(frame[key], str):
                errors.append(f'{label}: {key} must be text.')
        applicability = frame.get('applicability')
        if not isinstance(applicability, dict):
            errors.append(f'{label}: applicability must be an object keyed by process ID.')
            continue
        for pid, status in applicability.items():
            if pid not in process_ids:
                errors.append(f'{label}: process {pid} does not exist in this project.')
            if status not in ('required', 'optional'):
                errors.append(f'{label}: process {pid} must be required or optional; omit unused processes.')
    if errors:
        raise ScenarioValidationError(errors)
    return data


def frame_totals(project, frame):
    included = [p for p in project['processes'] if p['id'] in frame['applicability']]
    return {'process_count': len(included),
            'optional_count': sum(frame['applicability'][p['id']] == 'optional' for p in included),
            'manual_time': None if any(p['manual_time'] is None for p in included) else sum(p['manual_time'] for p in included),
            'auto_time': None if any(p['auto_time'] is None for p in included) else sum(p['auto_time'] for p in included)}
