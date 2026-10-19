"""Production-line simulation. Its event stream drives browser playback."""
import simpy

from scenario_schema import ScenarioValidationError, normalize_scenario, validate_scenario
from walking_geometry import (DEFAULT_LAYOUT_SCALE_PX_PER_M, DEFAULT_WALK_SPEED_M_PER_S,
                              box_center, station_destination, walking_metrics)


class ScenarioRuntimeError(Exception):
    pass


def run_scenario_simulation(scenario):
    data = validate_scenario(scenario)
    stations, operators, boxes = (data.get(k, {}) for k in ('stations', 'operators', 'boxes'))
    takt = data['takt_time']
    pixels_per_meter = data.get('layout_scale_px_per_m', DEFAULT_LAYOUT_SCALE_PX_PER_M)
    walking_speed = data.get('walking_speed_m_per_s', DEFAULT_WALK_SPEED_M_PER_S)
    env = simpy.Environment()
    stop = env.event()
    events = []
    # Required processes are per station, not per operator. A different
    # operator can deliver a part, process it, and pick up the finished part.
    required_processes = {sid: set() for sid in stations}
    for definition in operators.values():
        for step in definition['sequence']:
            if step['action'] == 'work' and step['loc'] in required_processes:
                required_processes[step['loc']].add(step['process'])

    machine = {}
    for sid, station in stations.items():
        has_part = bool(station.get('has_part'))
        part_event, space_event, completed_event = env.event(), env.event(), env.event()
        if has_part: part_event.succeed()
        else: space_event.succeed()
        if not required_processes[sid]: completed_event.succeed()
        machine[sid] = {'has_part': has_part, 'busy': False, 'done': None,
                        'part_event': part_event, 'space_event': space_event,
                        'completed_event': completed_event,
                        'completed_processes': set(), 'required_processes': required_processes[sid]}
    inventory = {bid: (b.get('start_count', 0) if b['type'] == 'in' else 0 if b['type'] == 'out' else int(bool(b.get('has_part')))) for bid, b in boxes.items()}
    box_part_event = {bid: env.event() for bid,b in boxes.items() if b['type'] == 'swip'}
    for bid,event in box_part_event.items():
        if inventory[bid]: event.succeed()

    def set_station_part(sid, has_part):
        state = machine[sid]
        state['has_part'] = has_part
        if has_part:
            state['space_event'] = env.event()
            state['completed_processes'].clear()
            state['completed_event'] = env.event()
            if not state['required_processes']:
                state['completed_event'].succeed()
            if not state['part_event'].triggered: state['part_event'].succeed()
        else:
            state['part_event'] = env.event()
            state['completed_processes'].clear()
            state['completed_event'] = env.event()
            if not state['space_event'].triggered: state['space_event'].succeed()

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
        state['completed_processes'].add(process['id'])
        if state['required_processes'].issubset(state['completed_processes']):
            if not state['completed_event'].triggered:
                state['completed_event'].succeed()
        state['busy'] = False
        done = state['done']
        state['done'] = None
        if done is not None and not done.triggered:
            done.succeed()

    def automatic_run(sid, op, process):
        yield env.timeout(process['auto_time'])
        if not stop.triggered:
            finish_machine(sid, op, process)

    def operator_run(op, definition):
        position = {'x': definition['x'], 'y': definition['y']}
        home = dict(position)
        holding = False
        sequence = definition['sequence']

        def travel(target, loc):
            nonlocal position
            # Walking distance is derived from world-space layout units, not screen zoom.
            distance_m, duration = walking_metrics(position, target, pixels_per_meter, walking_speed)
            if duration > 1e-12:
                emit('moving', op, loc, start=dict(position), end=dict(target),
                     duration=duration, distance_m=round(distance_m, 4),
                     walking_speed_m_per_s=walking_speed)
                yield env.timeout(duration)
            position = dict(target)
            emit('arrived', op, loc, position=dict(position))

        while not stop.triggered:
            cycle_start = env.now
            for index, step in enumerate(sequence):
                loc, action = step['loc'], step['action']
                destination = station_destination(stations, loc, step, position, definition) if loc in stations else box_center(boxes[loc])
                yield from travel(destination, loc)
                if stop.triggered:
                    return
                label = f"S{loc} ({stations[loc].get('name', loc)})" if loc in stations else boxes[loc].get('name', loc)
                # Cross-operator handoffs are synchronized with station inventory.
                # A collecting operator waits for incoming stock; a processing
                # operator waits for delivery; outbound transport waits for all
                # processes assigned to the station to finish.
                if action in ('pick', 'work') and loc in machine:
                    state = machine[loc]
                    while not stop.triggered:
                        if state['busy']:
                            emit('waiting', op, loc, reason=f'Waiting for {label} to finish processing.')
                            yield state['done']
                        elif not state['has_part']:
                            emit('waiting', op, loc, reason=f'Waiting for a part at {label}.')
                            yield state['part_event']
                        elif action == 'pick' and step.get('wait_for_process', False) and not state['required_processes'].issubset(state['completed_processes']):
                            emit('waiting', op, loc, reason=f'Waiting for processing at {label}.')
                            yield state['completed_event']
                        else:
                            break
                    if stop.triggered: return
                elif action == 'pick' and loc in box_part_event:
                    while inventory[loc] <= 0 and not stop.triggered:
                        emit('waiting', op, loc, reason=f'Waiting for a part at {label}.')
                        yield box_part_event[loc]
                    if stop.triggered: return
                if action == 'pick':
                    available = machine[loc]['has_part'] if loc in machine else inventory[loc] > 0
                    if holding or not available:
                        fail(op, loc, f'{op}: cannot pick from {label}; ' + ('already carrying a part.' if holding else 'no part is available.'))
                        return
                    if loc in machine:
                        set_station_part(loc, False)
                    else:
                        inventory[loc] -= 1
                        if loc in box_part_event and inventory[loc] == 0:
                            box_part_event[loc] = env.event()
                    holding = True
                    emit('pickup', op, loc)
                elif action == 'drop':
                    if not holding:
                        fail(op, loc, f'{op}: cannot drop at {label}; no part is being carried.')
                        return
                    if loc in machine:
                        state = machine[loc]
                        while state['busy'] or state['has_part']:
                            emit('waiting', op, loc, reason=f'Waiting for free space at {label}.')
                            yield state['space_event'] if state['has_part'] else state['done']
                            if stop.triggered: return
                        set_station_part(loc, True)
                    else:
                        capacity = boxes[loc].get('capacity', 1) if boxes[loc]['type'] in ('out', 'swip') else float('inf')
                        if inventory[loc] >= capacity:
                            fail(op, loc, f'{op}: cannot drop at {label}; location is full.')
                            return
                        inventory[loc] += 1
                        if loc in box_part_event and not box_part_event[loc].triggered:
                            box_part_event[loc].succeed()
                    holding = False
                    emit('dropoff', op, loc)
                elif action == 'work':
                    state = machine[loc]
                    if not state['has_part']:
                        fail(op, loc, f'{op}: cannot work at {label}; station has no part after waiting.')
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
