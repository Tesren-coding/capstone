"""Versioned scenario contract, migrations and validation shared by all routes.

Application release versions are independent from the scenario format version.
Migrations work on a deep copy; callers retain their original data.
"""
from copy import deepcopy
import json
import math

CURRENT_SCHEMA_VERSION = 2
EVENT_SCHEMA_VERSION = 1


class ScenarioValidationError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__('Scenario validation failed:\n' + '\n'.join(errors))


def is_number(value, minimum=0, positive=False):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and (value > minimum if positive else value >= minimum))


def normalize_scenario(scenario):
    """Upgrade old cycle_time stations without changing the caller's data."""
    if not isinstance(scenario, dict):
        raise ScenarioValidationError(['Scenario must be an object.'])
    data = deepcopy(scenario)
    version = scenario.get('schema_version', 1)
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ScenarioValidationError(['schema_version must be a positive integer.'])
    if version > CURRENT_SCHEMA_VERSION:
        raise ScenarioValidationError([f'Scenario format v{version} is newer than this app supports (v{CURRENT_SCHEMA_VERSION}). Update the app to import it.'])
    while version < CURRENT_SCHEMA_VERSION:
        migration = MIGRATIONS.get(version)
        if migration is None:
            raise ScenarioValidationError([f'No supported migration from scenario format v{version}.'])
        data = migration(data)
        version += 1
        data['schema_version'] = version
    data['schema_version'] = CURRENT_SCHEMA_VERSION
    for key in ('stations', 'operators', 'boxes'):
        data.setdefault(key, {})
    for station in data['stations'].values() if isinstance(data['stations'], dict) else []:
        if isinstance(station, dict) and isinstance(station.get('processes'), list):
            times = [p.get(k) for p in station['processes'] if isinstance(p, dict)
                     for k in ('manual_time', 'auto_time')]
            if all(is_number(t) for t in times):
                station['cycle_time'] = sum(times)
    return data



def migrate_v1_to_v2(data):
    station_map = data.get('stations', {})
    operator_map = data.get('operators', {})
    if not isinstance(station_map, dict) or not isinstance(operator_map, dict):
        raise ScenarioValidationError(['Stations and operators must be objects.'])
    for station in station_map.values():
        if not isinstance(station, dict):
            continue
        if 'processes' not in station:
            station['processes'] = [{'id': 'p1', 'name': 'Process 1',
                                     'manual_time': station.get('cycle_time', 10), 'auto_time': 0}]
        processes = station.get('processes')
        if isinstance(processes, list) and all(isinstance(p, dict) for p in processes):
            # Retain a derived total for old integrations; processes are authoritative.
            times = [p.get(k) for p in processes for k in ('manual_time', 'auto_time')]
            if all(is_number(t) for t in times):
                station['cycle_time'] = sum(times)
    for operator in operator_map.values():
        if not isinstance(operator, dict):
            continue
        sequence = operator.get('sequence', [])
        if not isinstance(sequence, list):
            continue
        for step in sequence:
            if not isinstance(step, dict):
                continue
            if step.get('loc') is not None:
                step['loc'] = str(step['loc'])
            if step.get('action') == 'work' and 'process' not in step:
                station = (data.get('stations') or {}).get(step.get('loc'), {})
                processes = station.get('processes', [])
                if isinstance(processes, list) and len(processes) == 1 and isinstance(processes[0], dict):
                    step['process'] = processes[0].get('id')
    return data


MIGRATIONS = {1: migrate_v1_to_v2}

def validate_scenario(scenario, require_runnable=True):
    data = normalize_scenario(scenario)
    errors = []
    try:
        json.dumps(data, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ScenarioValidationError(['Scenario must contain valid JSON values and finite numbers.']) from exc
    if not is_number(data.get('takt_time'), positive=True):
        errors.append('Takt time must be a positive number of minutes.')
    for key in ('stations', 'operators', 'boxes'):
        if not isinstance(data.get(key, {}), dict):
            errors.append(f'{key} must be an object.')
    if errors:
        raise ScenarioValidationError(errors)
    stations, operators, boxes = (data.get(k, {}) for k in ('stations', 'operators', 'boxes'))
    if require_runnable and (not stations or not operators):
        errors.append('Scenario needs at least one station and one operator.')
    if set(stations) & set(boxes):
        errors.append('Station and box IDs must be unique across the layout.')
    for sid in stations:
        if not isinstance(sid, str) or not sid.isascii() or not sid.isdigit() or not sid.strip('0'):
            errors.append('Station IDs must be positive integer strings, such as "1".')
    for key in (*operators, *boxes):
        if not isinstance(key, str) or not key:
            errors.append('Operator and box IDs must be non-empty strings.')
        elif key in ('__proto__', 'constructor', 'prototype'):
            errors.append(f'ID {key} is reserved; choose another operator or box ID.')
    locations = {**stations, **boxes}
    for loc, item in locations.items():
        if not isinstance(item, dict):
            errors.append(f'Location {loc} must be an object.')
            continue
        if not isinstance(item.get('name'), str) or not item['name'].strip():
            errors.append(f'Location {loc} needs a name.')
        if 'has_part' in item and not isinstance(item['has_part'], bool):
            errors.append(f'Location {loc}: has_part must be true or false.')
        if any(not is_number(item.get(k), minimum=-float('inf')) for k in ('x', 'y')):
            errors.append(f'Location {loc} needs finite X and Y coordinates.')
        if any(not is_number(item.get(k), positive=True) for k in ('w', 'h')):
            errors.append(f'Location {loc} needs positive width and height.')
    for sid, station in stations.items():
        if not isinstance(station, dict):
            continue
        processes = station.get('processes')
        if not isinstance(processes, list) or not processes:
            errors.append(f'Station S{sid} needs at least one process.')
            continue
        seen = set()
        for index, process in enumerate(processes):
            label = f'Station S{sid}, process {index + 1}'
            if not isinstance(process, dict):
                errors.append(f'{label} must be an object.')
                continue
            pid = process.get('id')
            if not isinstance(pid, str) or not pid or pid in seen:
                errors.append(f'{label} needs a unique process ID.')
            else:
                seen.add(pid)
            if not isinstance(process.get('name'), str) or not process['name'].strip():
                errors.append(f'{label} needs a name.')
            manual, automatic = process.get('manual_time'), process.get('auto_time')
            if not is_number(manual) or not is_number(automatic):
                errors.append(f'{label}: manual and automatic time must be finite numbers ≥ 0.')
            elif manual + automatic <= 0:
                errors.append(f'{label}: total processing time must be greater than zero.')
    for bid, box in boxes.items():
        if not isinstance(box, dict):
            continue
        kind = box.get('type')
        if kind not in ('in', 'out', 'swip'):
            errors.append(f'Box {bid} has an invalid type.')
        for field, minimum in [('start_count', 0)] if kind == 'in' else [('capacity', 1)] if kind == 'out' else []:
            value = box.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
                errors.append(f'Box {bid}: {field} must be an integer ≥ {minimum}.')
    for op, operator in operators.items():
        if not isinstance(operator, dict):
            errors.append(f'Operator {op} must be an object.')
            continue
        if not isinstance(operator.get('name'), str) or not operator['name'].strip():
            errors.append(f'Operator {op} needs a name.')
        color = operator.get('color')
        if not isinstance(color, list) or len(color) != 3 or any(not isinstance(c, int) or isinstance(c, bool) or not 0 <= c <= 255 for c in color):
            errors.append(f'Operator {op}: color must contain three integer RGB values from 0 to 255.')
        if any(not is_number(operator.get(k), minimum=-float('inf')) for k in ('x', 'y')):
            errors.append(f'Operator {op} needs finite X and Y coordinates.')
        sequence = operator.get('sequence')
        if not isinstance(sequence, list) or (require_runnable and not sequence):
            errors.append(f'Operator {op} needs a sequence list; running requires at least one step.')
            continue
        carrying = False
        for index, step in enumerate(sequence):
            label = f'Operator {op}, step {index + 1}'
            if not isinstance(step, dict):
                errors.append(f'{label} must be an object.')
                continue
            action, loc = step.get('action'), step.get('loc')
            if action not in ('pick', 'work', 'drop'):
                errors.append(f'{label}: invalid action.')
            if not isinstance(loc, str):
                errors.append(f'{label}: location must be a string ID (or empty while editing).')
                continue
            if not require_runnable:
                if action == 'work' and not isinstance(step.get('process', ''), str):
                    errors.append(f'{label}: process must be a string ID.')
                continue
            if not isinstance(loc, str) or loc not in locations:
                errors.append(f'{label}: select a valid location.')
            if action == 'work':
                if loc not in stations:
                    errors.append(f'{label}: Work must target a station.')
                elif isinstance(stations[loc], dict):
                    processes = stations[loc].get('processes', [])
                    ids = [p.get('id') for p in processes if isinstance(p, dict)] if isinstance(processes, list) else []
                    if not isinstance(step.get('process'), str) or step.get('process') not in ids:
                        errors.append(f'{label}: select a valid process at S{loc}.')
                if carrying:
                    errors.append(f'{label}: drop the carried part before working.')
            elif action == 'pick':
                if carrying:
                    errors.append(f'{label}: already carrying a part.')
                carrying = True
            elif action == 'drop':
                if not carrying:
                    errors.append(f'{label}: no carried part to drop.')
                carrying = False
        if require_runnable and carrying:
            errors.append(f'Operator {op}: sequence must drop its last carried part before repeating.')
    if errors:
        raise ScenarioValidationError(errors)
    return data


