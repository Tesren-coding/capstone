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
    # Runtime diagnostics are evaluated on simulated time, not playback time.
    # A short wait is legitimate when another operator can supply the part.
    # A sustained absence of processing/material movement is not a completed run.
    max_stall_minutes = max(5.0, 3.0 * takt)
    # Each operator waiting for a required incoming part has an independent,
    # strict timeout. Progress by another operator does not reset this clock.
    operator_wait_limit_minutes = 5.0
    last_progress_time = 0.0
    waiting_by_operator = {}
    planned_waits = set()  # intentional Wait tasks are NOT blocked operators
    last_output_time = None
    # Only evaluate takt-based finished output when at least one operator has
    # an explicit delivery task to an OUT box. A decorative OUT box alone is
    # not proof that the scenario models finished-goods output.
    expects_finished_output = any(
        step['action'] == 'drop'
        and step['loc'] in boxes
        and boxes[step['loc']]['type'] == 'out'
        for definition in operators.values()
        for step in definition['sequence']
    )
    productive_statuses = {'pickup', 'dropoff', 'manual_start', 'process_complete'}
    # Track completed work individually for each part at a station. Processes
    # assigned to one station are independent; one process is NOT a prerequisite
    # for collection or for starting another process.
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
        # This declaration applies ONLY to the original part in the station.
        # A later delivered part always starts with no completed processes.
        initially_complete = has_part and station.get('starting_part_processed', False)
        completed_processes = set(required_processes[sid]) if initially_complete else set()
        if required_processes[sid].issubset(completed_processes):
            completed_event.succeed()
        machine[sid] = {'has_part': has_part, 'busy': False, 'done': None,
                        'part_event': part_event, 'space_event': space_event,
                        'completed_event': completed_event,
                        'completed_processes': completed_processes, 'required_processes': required_processes[sid]}
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
        nonlocal last_progress_time
        if not stop.triggered:
            if status in productive_statuses:
                last_progress_time = env.now
            if op is not None:
                if status == 'planned_wait_start':
                    planned_waits.add(op)
                elif status == 'planned_wait_end':
                    planned_waits.discard(op)
                    # A deliberate pause is not an unexplained line stall.
                    last_progress_time = env.now
                if status == 'waiting':
                    waiting_by_operator[op] = (loc, extra.get('reason', 'Waiting for material or processing'))
                elif status in productive_statuses or status in ('moving', 'idle'):
                    waiting_by_operator.pop(op, None)
            events.append({'time': env.now, 'status': status, 'operator': op, 'loc': loc, **extra})

    def fail(op, loc, reason):
        emit('blocked', op, loc, reason=reason)
        if not stop.triggered:
            stop.succeed()

    def progress_watchdog():
        # The horizon timeout alone used to mark permanently stalled lines as
        # complete. Check for real material/process progress throughout a run.
        interval = max(.1, min(takt / 4.0, 1.0))
        while not stop.triggered:
            yield env.timeout(interval)
            if stop.triggered:
                return
            # Output cadence is measured between finished parts. The first
            # part gets a warm-up allowance of three takt periods; subsequent
            # finished parts must meet the configured takt target.
            if expects_finished_output:
                if last_output_time is None and env.now > max_stall_minutes + 1e-7:
                    fail(None, None, f'No finished parts delivered to OUT after {env.now:.1f} min (takt target {takt:g} min). Check production flow, process times and material availability.')
                    return
                if last_output_time is not None and env.now - last_output_time > takt + 1e-7:
                    fail(None, None, f'Output below takt target: no finished part delivered for {env.now - last_output_time:.2f} min; takt target is {takt:g} min.')
                    return
            # The per-operator wait timer below supplies a more precise error
            # than this line-wide watchdog. Never preempt an active wait with a
            # generic 'no progress' message before its own five minutes expire.
            if waiting_by_operator or planned_waits:
                continue
            elapsed = env.now - last_progress_time
            if elapsed + 1e-8 < max_stall_minutes:
                continue
            waiting = [f'{op}: {reason}' for op, (_, reason) in sorted(waiting_by_operator.items())]
            if waiting:
                details = '; '.join(waiting[:4])
                if len(waiting) > 4:
                    details += f'; and {len(waiting) - 4} more operators'
                if len(waiting_by_operator) == len(operators) and not any(state['busy'] for state in machine.values()):
                    kind = 'Deadlock / starvation'
                else:
                    kind = 'Material-flow stall / starvation'
                op, (loc, _) = next(iter(sorted(waiting_by_operator.items())))
                fail(op, loc, f'{kind}: no material or processing progress for {elapsed:.1f} min. {details}')
            else:
                fail(None, None, f'Simulation stalled: no material or processing progress for {elapsed:.1f} min. Check the assigned tasks, source parts and cycle time.')
            return

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
        nonlocal last_output_time
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
                action = step['action']
                if action == 'wait':
                    # A planned pause is not a material/processing blockage.
                    # Stay exactly where the operator is, even if carrying a part.
                    duration = step['duration']
                    emit('planned_wait_start', op, None, duration=duration, step=index + 1)
                    yield env.timeout(duration)
                    if stop.triggered:
                        return
                    emit('planned_wait_end', op, None, step=index + 1)
                    continue
                loc = step['loc']
                destination = station_destination(stations, loc, step, position, definition) if loc in stations else box_center(boxes[loc])
                yield from travel(destination, loc)
                if stop.triggered:
                    return
                label = f"S{loc} ({stations[loc].get('name', loc)})" if loc in stations else boxes[loc].get('name', loc)
                # Inbound handoffs can wait for an absent part to arrive.
                # Occupied/busy stations are conflicts for delivery, and
                # competing operators cannot wait for active station work.
                # No station-wide process-completion sequence is required.
                if action in ('pick', 'work') and loc in machine:
                    state = machine[loc]
                    wait_started = None
                    while not stop.triggered:
                        if state['busy']:
                            fail(op, loc, f'{op}, step {index + 1}: cannot {"collect a part from" if action == "pick" else "start work at"} {label}; station is still processing another operation.')
                            return
                        if state['has_part']:
                            break
                        if wait_started is None:
                            wait_started = env.now
                            emit('waiting', op, loc, reason=f'Waiting for a part at {label} to {"collect" if action == "pick" else "process"}.')
                        elapsed = env.now - wait_started
                        remaining = operator_wait_limit_minutes - elapsed
                        if remaining <= 1e-8:
                            fail(op, loc, f'{op}, step {index + 1}: unable to {"collect a part from" if action == "pick" else "start processing at"} {label} after waiting {operator_wait_limit_minutes:g} simulation minutes; the station has no part.')
                            return
                        # A new part can arrive from another operator during the
                        # five-minute window. The deadline never resets if a
                        # different operator consumes that part first.
                        yield state['part_event'] | env.timeout(remaining)
                    if stop.triggered: return
                elif action == 'pick' and loc in box_part_event:
                    # SWIP pickups are immediate prerequisites, not deferred
                    # handoffs. An empty SWIP must stop the run at this step.
                    if inventory[loc] <= 0:
                        fail(op, loc, f'{op}, step {index + 1}: cannot collect from {label}; SWIP box is empty (no part available).')
                        return
                if action == 'pick':
                    available = machine[loc]['has_part'] if loc in machine else inventory[loc] > 0
                    if holding or not available:
                        fail(op, loc, f'{op}: cannot pick from {label}; ' + ('already carrying a part.' if holding else 'no part is available.'))
                        return
                    if loc in machine:
                        # Processes sharing a station are independent, not a
                        # mandatory ordered route. Picking an available part
                        # does not require other assigned work to be complete.
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
                        if state['busy']:
                            fail(op, loc, f'{op}, step {index + 1}: cannot deliver to {label}; the station is still processing another part.')
                            return
                        if state['has_part']:
                            fail(op, loc, f'{op}, step {index + 1}: cannot deliver to {label}; the station already contains a part.')
                            return
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
                    if loc in boxes and boxes[loc]['type'] == 'out':
                        # The takt target applies only when the scenario
                        # explicitly delivers finished parts to an OUT box.
                        if last_output_time is not None and env.now - last_output_time > takt + 1e-7:
                            fail(op, loc, f'Output below takt target: {env.now - last_output_time:.2f} min between finished parts; takt target is {takt:g} min at {label}.')
                            return
                        last_output_time = env.now
                elif action == 'work':
                    state = machine[loc]
                    if not state['has_part']:
                        fail(op, loc, f'{op}: cannot work at {label}; station has no part after waiting.')
                        return
                    process = next(p for p in stations[loc]['processes'] if p['id'] == step['process'])
                    if process['id'] in state['completed_processes']:
                        fail(op, loc, f'{op}: {process["name"]} was already completed for the part at {label}. Check for duplicate process assignments.')
                        return
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
    env.process(progress_watchdog())
    horizon = takt * 100
    env.run(until=simpy.events.AnyOf(env, [stop, env.timeout(horizon)]))
    if not stop.triggered:
        if expects_finished_output and last_output_time is None:
            fail(None, None, 'Simulation completed without delivering any finished parts to OUT.')
        elif planned_waits:
            fail(None, None, 'Simulation horizon reached while operators were still completing explicitly assigned Wait tasks.')
        elif waiting_by_operator:
            op, (loc, reason) = next(iter(sorted(waiting_by_operator.items())))
            fail(op, loc, f'Simulation reached its limit with unresolved waiting: {op}: {reason}')
        elif env.now - last_progress_time >= max_stall_minutes:
            fail(None, None, 'Simulation reached its limit without recent processing or material movement.')
        else:
            emit('simulation_complete', reason='Completed 100 takt periods.')
    return events, takt
