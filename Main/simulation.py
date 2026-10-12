"""Production-line simulation. Its event stream drives browser playback."""
import math
import simpy

from scenario_schema import ScenarioValidationError, normalize_scenario, validate_scenario

WALK_SPEED = 1000.0  # layout pixels per simulated minute


class ScenarioRuntimeError(Exception):
    pass


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
