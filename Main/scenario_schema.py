"""Versioned scenario contract, migrations and validation shared by all routes.

Application release versions are independent from the scenario format version.
Migrations work on a deep copy; callers retain their original data.
"""
from copy import deepcopy
import json
import hashlib
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
    # Operator IDs also serve as their display names. Keep the name field for
    # backwards compatibility with stored v1/v2 scenarios and existing clients,
    # but overwrite old custom names on the normalized COPY (not the caller).
    if isinstance(data['operators'], dict):
        for operator_id, operator in data['operators'].items():
            if isinstance(operator, dict):
                operator['name'] = operator_id
                # Older task editors could retain a station standing side when
                # a Pick/Drop location was changed to an IN, OUT or SWIP box.
                # Material boxes use their centre; the unused side is safe to
                # remove on the normalized *copy*, without changing the task.
                boxes = data.get('boxes', {})
                if isinstance(boxes, dict) and isinstance(operator.get('sequence'), list):
                    for step in operator['sequence']:
                        if not isinstance(step, dict):
                            continue
                        box = boxes.get(step.get('loc')) if isinstance(step.get('loc'), str) else None
                        if isinstance(box, dict) and box.get('type') in ('in', 'out', 'swip'):
                            step.pop('standing_side', None)
    for station in data['stations'].values() if isinstance(data['stations'], dict) else []:
        if isinstance(station, dict):
            # Old saved scenarios must retain the original behavior: a starting
            # part still requires the station's assigned processing.
            station.setdefault('starting_part_processed', False)
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

def validate_scenario(scenario, require_runnable=True, skip_planning_review=False):
    data = normalize_scenario(scenario)
    errors = []
    try:
        json.dumps(data, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ScenarioValidationError(['Scenario must contain valid JSON values and finite numbers.']) from exc
    if not is_number(data.get('takt_time'), positive=True):
        errors.append('Takt time must be a positive number of minutes.')
    # Optional in v2 for backward compatibility with saved scenarios.
    if not is_number(data.get('layout_scale_px_per_m', 50), positive=True) or data.get('layout_scale_px_per_m', 50) > 10000:
        errors.append('Layout scale must be greater than 0 and no more than 10000 pixels per meter.')
    if not is_number(data.get('walking_speed_m_per_s', 1.2), positive=True) or data.get('walking_speed_m_per_s', 1.2) > 5:
        errors.append('Walking speed must be greater than 0 and no more than 5 m/s.')
    for key in ('stations', 'operators', 'boxes', 'dimensions'):
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
        if not isinstance(station.get('starting_part_processed'), bool):
            errors.append(f'Station S{sid}: starting part status must be Not Processed or Already Processed.')
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
        if kind not in ('in', 'out', 'swip', 'direction'):
            errors.append(f'Box {bid} has an invalid type.')
        if kind == 'direction':
            if 'rotation' in box and (not isinstance(box['rotation'], (int, float)) or
                                       isinstance(box['rotation'], bool) or not math.isfinite(box['rotation'])):
                errors.append(f'Box {bid}: rotation must be a finite number of degrees.')
            for field in ('flip_horizontal', 'flip_vertical'):
                if field in box and not isinstance(box[field], bool):
                    errors.append(f'Box {bid}: {field} must be true or false.')
        for field, minimum in [('start_count', 0)] if kind == 'in' else [('capacity', 1)] if kind == 'out' else []:
            value = box.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
                errors.append(f'Box {bid}: {field} must be an integer ≥ {minimum}.')
    # Rulers are non-inventory annotations, not simulation locations.
    # Legacy scenarios without dimensions remain fully supported.
    for did, dim in data.get('dimensions', {}).items():
        if not isinstance(did, str) or not did or did in ('__proto__', 'constructor', 'prototype'):
            errors.append('Dimension IDs must be nonempty safe strings.')
        if not isinstance(dim, dict):
            errors.append(f'Dimension {did} must be an object.')
            continue
        for field in ('x', 'y', 'x2', 'y2'):
            if not is_number(dim.get(field), minimum=-float('inf')):
                errors.append(f'Dimension {did}: {field} must be finite.')
        if 'offset' in dim and not is_number(dim['offset'], minimum=-float('inf')):
            errors.append(f'Dimension {did}: offset must be a finite canvas distance.')
        for field in ('start_anchor', 'end_anchor'):
            anchor=dim.get(field)
            if anchor is None:
                continue
            if not isinstance(anchor, dict) or anchor.get('type') not in ('station', 'box'):
                errors.append(f'Dimension {did}: {field} must reference a station or box.')
                continue
            # Deleted anchors are allowed: fallback points keep old annotations usable.
            if not isinstance(anchor.get('id'), str) or anchor.get('id') in ('__proto__', 'constructor', 'prototype') or any(
                not is_number(anchor.get(axis)) or anchor[axis] > 1 for axis in ('rx', 'ry')
            ):
                errors.append(f'Dimension {did}: {field} has invalid coordinates.')
    occupied_operator_slots = set()
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
        # Optional v2 layout metadata; old files keep their original positions.
        # A station ID is a string because JSON object keys are strings.
        if 'attached_to' in operator:
            anchor = operator['attached_to']
            if (not isinstance(anchor, dict) or
                set(anchor) != {'station_id', 'side'} or
                not isinstance(anchor.get('station_id'), str) or
                anchor['station_id'] not in stations or
                anchor.get('side') not in ('top', 'right', 'bottom', 'left')):
                errors.append(f'Operator {op}: attached_to must identify an existing station and one of its four sides.')
            else:
                slot = (anchor['station_id'], anchor['side'])
                if slot in occupied_operator_slots:
                    errors.append(f'Operator {op}: station side S{slot[0]} {slot[1]} is already occupied.')
                occupied_operator_slots.add(slot)
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
            if action == 'wait':
                if not is_number(step.get('duration'), positive=True):
                    errors.append(f'{label}: Wait duration must be a finite number greater than 0 minutes.')
                if step.get('standing_side') is not None:
                    errors.append(f'{label}: Wait has no standing-side destination.')
                # Wait is deliberate inactivity at the operator's current
                # position. It has no location and does not affect carrying.
                continue
            if 'wait_for_process' in step and (action != 'pick' or not isinstance(step['wait_for_process'], bool)):
                errors.append(f'{label}: wait_for_process must be a boolean on a Pick action.')
            # A standing side identifies where this operator performs the step.
            # Older saves omit the setting and use the nearest available side.
            standing_side = step.get('standing_side')
            if standing_side is not None:
                if standing_side not in ('top', 'right', 'bottom', 'left'):
                    errors.append(f'{label}: standing side must be top, right, bottom or left.')
                elif not isinstance(loc, str) or loc not in stations:
                    errors.append(f'{label}: standing side can only be assigned at a station.')
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
            elif loc in boxes and isinstance(boxes[loc], dict) and boxes[loc].get('type') == 'direction':
                errors.append(f'{label}: Line Direction is a visual marker, not a material location.')
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
    if require_runnable and not skip_planning_review and planning_review_required(data) and not planning_reviewed(data):
        errors.append('Generated line needs material-flow review. In Line Builder, complete Pick/Drop steps and parts, then use Check setup and mark reviewed. Changes after review require another check.')
    if errors:
        raise ScenarioValidationError(errors)
    return data



def planning_review_required(data):
    origin = data.get('planning_origin')
    return isinstance(origin, dict) and origin.get('material_review_required') is True


def scenario_review_fingerprint(data):
    # Core state only: provenance is a historical snapshot, not live configuration.
    core = {key: data.get(key) for key in ('schema_version', 'takt_time', 'stations', 'operators', 'boxes')}
    return hashlib.sha256(json.dumps(core, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()


def planning_reviewed(data):
    return planning_review_required(data) and data['planning_origin'].get('review_fingerprint') == scenario_review_fingerprint(data)


def review_planning_scenario(original):
    data = validate_scenario(original, skip_planning_review=True)
    if not planning_review_required(data):
        raise ScenarioValidationError(['This scenario was not generated from a planning setup.'])
    actions = [s['action'] for op in data['operators'].values() for s in op['sequence']]
    if 'work' in actions and 'drop' not in actions and not any(station.get('has_part') for station in data['stations'].values()):
        raise ScenarioValidationError(['This Work-only draft has no starting parts or deliveries. Add input parts and Pick/Drop steps in the operator sequences before marking it reviewed.'])
    data['planning_origin']['review_fingerprint'] = scenario_review_fingerprint(data)
    return data
