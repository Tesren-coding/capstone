"""Production-line simulation. This event stream also drives browser playback."""
from copy import deepcopy
import math
import simpy

WALK_SPEED = 1000.0  # layout pixels per simulated minute


class ScenarioValidationError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__('Scenario validation failed:\n' + '\n'.join(errors))


class ScenarioRuntimeError(Exception):
    pass


def is_number(value, minimum=0, positive=False):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and (value > minimum if positive else value >= minimum))


def normalize_scenario(scenario):
    """Upgrade old cycle_time stations without changing the caller's data."""
    if not isinstance(scenario, dict):
        raise ScenarioValidationError(['Scenario must be an object.'])
    data = deepcopy(scenario)
    data['schema_version'] = 2
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


def validate_scenario(scenario):
    data = normalize_scenario(scenario)
    errors = []
    if not is_number(data.get('takt_time'), positive=True):
        errors.append('Takt time must be a positive number of minutes.')
    for key in ('stations', 'operators', 'boxes'):
        if not isinstance(data.get(key, {}), dict):
            errors.append(f'{key} must be an object.')
    if errors:
        raise ScenarioValidationError(errors)
    stations, operators, boxes = (data.get(k, {}) for k in ('stations', 'operators', 'boxes'))
    if not stations or not operators:
        errors.append('Scenario needs at least one station and one operator.')
    if set(stations) & set(boxes):
        errors.append('Station and box IDs must be unique across the layout.')
    locations = {**stations, **boxes}
    for loc, item in locations.items():
        if not isinstance(item, dict):
            errors.append(f'Location {loc} must be an object.')
            continue
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
        if any(not is_number(operator.get(k), minimum=-float('inf')) for k in ('x', 'y')):
            errors.append(f'Operator {op} needs finite X and Y coordinates.')
        sequence = operator.get('sequence')
        if not isinstance(sequence, list) or not sequence:
            errors.append(f'Operator {op} needs a non-empty sequence.')
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
        if carrying:
            errors.append(f'Operator {op}: sequence must drop its last carried part before repeating.')
    if errors:
        raise ScenarioValidationError(errors)
    return data


def run_scenario_simulation(scenario):
    data = validate_scenario(scenario)
    stations, operators, boxes = (data.get(k, {}) for k in ('stations', 'operators', 'boxes'))
    takt = data['takt_time']
    env = simpy.Environment()
    stop = env.event()
    events = []
    machine = {sid: {'has_part': bool(s.get('has_part')), 'busy': False, 'done': None} for sid, s in stations.items()}
    inventory = {bid: (b.get('start_count', 0) if b['type'] == 'in' else 0 if b['type'] == 'out' else int(bool(b.get('has_part')))) for bid, b in boxes.items()}

    def emit(status, op=None, loc=None, **extra):
        if not stop.triggered:
            events.append({'time': env.now, 'status': status, 'operator': op, 'loc': loc, **extra})

    def fail(op, loc, reason):
        emit('blocked', op, loc, reason=reason)
        if not stop.triggered:
            stop.succeed()

    def finish_machine(sid, op, process):
        state = machine[sid]
        emit('process_complete', op, sid, process=process['id'])
        state['busy'] = False
        done = state['done']
        state['done'] = None
        if done is not None and not done.triggered:
            done.succeed()

    def automatic_run(sid, op, process):
        yield env.timeout(process['auto_time'])
        if not stop.triggered:
            finish_machine(sid, op, process)

    def center(loc):
        item = stations.get(loc, boxes.get(loc))
        return {'x': item['x'] + item['w'] / 2, 'y': item['y'] + item['h'] / 2}

    def operator_run(op, definition):
        position = {'x': definition['x'], 'y': definition['y']}
        home = dict(position)
        holding = False
        sequence = definition['sequence']

        def travel(target, loc):
            nonlocal position
            duration = math.hypot(target['x'] - position['x'], target['y'] - position['y']) / WALK_SPEED
            if duration:
                emit('moving', op, loc, start=dict(position), end=dict(target), duration=duration)
                yield env.timeout(duration)
            position = dict(target)
            emit('arrived', op, loc, position=dict(position))

        while not stop.triggered:
            cycle_start = env.now
            for index, step in enumerate(sequence):
                loc, action = step['loc'], step['action']
                yield from travel(center(loc), loc)
                if stop.triggered:
                    return
                label = f"S{loc} ({stations[loc].get('name', loc)})" if loc in stations else boxes[loc].get('name', loc)
                # Picking/next-process work can wait for the existing cycle. Drops never wait.
                if action in ('pick', 'work') and loc in machine:
                    while machine[loc]['busy']:
                        emit('waiting', op, loc, reason=f'Waiting for {label} to finish processing.')
                        yield machine[loc]['done']
                        if stop.triggered:
                            return
                if action == 'pick':
                    available = machine[loc]['has_part'] if loc in machine else inventory[loc] > 0
                    if holding or not available:
                        fail(op, loc, f'{op}: cannot pick from {label}; ' + ('already carrying a part.' if holding else 'no part is available.'))
                        return
                    if loc in machine:
                        machine[loc]['has_part'] = False
                    else:
                        inventory[loc] -= 1
                    holding = True
                    emit('pickup', op, loc)
                elif action == 'drop':
                    if not holding:
                        fail(op, loc, f'{op}: cannot drop at {label}; no part is being carried.')
                        return
                    if loc in machine:
                        state = machine[loc]
                        if state['busy']:
                            fail(op, loc, f'{op}: cannot move/drop a part into {label}; station is in process.')
                            return
                        if state['has_part']:
                            fail(op, loc, f'{op}: cannot drop at {label}; station already contains a part.')
                            return
                        state['has_part'] = True
                    else:
                        capacity = boxes[loc].get('capacity', 1) if boxes[loc]['type'] in ('out', 'swip') else float('inf')
                        if inventory[loc] >= capacity:
                            fail(op, loc, f'{op}: cannot drop at {label}; location is full.')
                            return
                        inventory[loc] += 1
                    holding = False
                    emit('dropoff', op, loc)
                elif action == 'work':
                    state = machine[loc]
                    if not state['has_part']:
                        fail(op, loc, f'{op}: cannot work at {label}; station has no part.')
                        return
                    process = next(p for p in stations[loc]['processes'] if p['id'] == step['process'])
                    state['busy'] = True
                    state['done'] = env.event()
                    emit('manual_start', op, loc, process=process['id'], process_name=process['name'],
                         duration=process['manual_time'], auto_time=process['auto_time'])
                    if process['manual_time']:
                        yield env.timeout(process['manual_time'])
                    if stop.triggered:
                        return
                    if process['auto_time']:
                        emit('auto_start', op, loc, process=process['id'], process_name=process['name'], duration=process['auto_time'])
                        env.process(automatic_run(loc, op, process))
                    else:
                        finish_machine(loc, op, process)
                    emit('operator_ready', op, loc)
            yield from travel(home, None)
            remaining = cycle_start + takt - env.now
            if remaining > 0:
                emit('idle', op, None)
                yield env.timeout(remaining)
            if stop.triggered:
                return
    for op, definition in operators.items():
        env.process(operator_run(op, definition))
    horizon = takt * 100
    env.run(until=simpy.events.AnyOf(env, [stop, env.timeout(horizon)]))
    if not stop.triggered:
        emit('simulation_complete', reason='Completed 100 takt periods.')
    return events, takt
