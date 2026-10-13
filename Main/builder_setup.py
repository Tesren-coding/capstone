"""Versioned station mappings and an explicit balance-plan to scenario conversion."""
from copy import deepcopy
import json
import re
from balancing_schema import validate_plan, active_step
from line_layout import c_layout
from scenario_schema import CURRENT_SCHEMA_VERSION, ScenarioValidationError, validate_scenario

SETUP_SCHEMA_VERSION = 1
MODES = ('work_only', 'single_operator_flow')
COLORS = [[38, 111, 184], [43, 148, 99], [202, 118, 47], [143, 83, 174], [190, 68, 88]]


def setup_from_plan(plan, filename=None, revision=None):
    plan = validate_plan(plan)
    active = [s for s in plan['steps'] if active_step(plan, s)]
    return validate_setup({'document_type': 'builder_setup', 'schema_version': SETUP_SCHEMA_VERSION,
        'setup_name': plan['plan_name'] + ' — line setup', 'source': {'plan': plan, 'filename': filename, 'revision': revision},
        'stations': [{'id': str(i+1), 'name': s['name']} for i, s in enumerate(active)],
        'mapping': {s['id']: str(i+1) for i, s in enumerate(active)}, 'next_station_id': len(active)+1,
        'mode': 'work_only', 'input_count': 150, 'output_capacity': 200,
        'layout': {'shape': 'c', 'break_after_station_id': next((str(i+1) for i,s in enumerate(active) if s['id'] == (plan.get('line_layout') or {}).get('break_after_step_id')), None)}})


def validate_setup(original):
    if not isinstance(original, dict) or original.get('document_type') != 'builder_setup':
        raise ScenarioValidationError(['Choose a Line Builder setup JSON file.'])
    version = original.get('schema_version')
    if type(version) is not int or version != SETUP_SCHEMA_VERSION:
        raise ScenarioValidationError([f'Unsupported builder setup format {version}; this app supports format {SETUP_SCHEMA_VERSION}.'])
    data = deepcopy(original)
    try: json.dumps(data, allow_nan=False)
    except (ValueError, TypeError) as exc: raise ScenarioValidationError(['Setup must contain valid JSON and finite numbers.']) from exc
    errors = []
    if not isinstance(data.get('setup_name'), str) or not data['setup_name'].strip(): errors.append('Name the line setup.')
    source = data.get('source')
    if not isinstance(source, dict): raise ScenarioValidationError(['Select a balance plan first.'])
    source['plan'] = validate_plan(source.get('plan'))
    for key in ('filename', 'revision'):
        if source.get(key) is not None and not isinstance(source[key], str): errors.append(f'Source {key} must be text or null.')
    if data.get('mode') not in MODES: errors.append('Choose Work steps only or single-operator transport.')
    for key, minimum in [('next_station_id', 1), ('input_count', 1), ('output_capacity', 1)]:
        if type(data.get(key)) is not int or data[key] < minimum: errors.append(f'{key} must be an integer ≥ {minimum}.')
    stations, mapping = data.get('stations'), data.get('mapping')
    if not isinstance(stations, list) or not isinstance(mapping, dict): errors.append('Stations must be a list and mapping must be an object.')
    if errors: raise ScenarioValidationError(errors)
    ids = set()
    for index, station in enumerate(stations):
        if not isinstance(station, dict): errors.append(f'Station {index+1} must be an object.'); continue
        sid = station.get('id')
        if not isinstance(sid, str) or not re.fullmatch(r'[1-9][0-9]*', sid) or int(sid) > 9007199254740991 or sid in ids:
            errors.append('Station IDs must be unique positive whole-number strings.')
        else: ids.add(sid)
        if not isinstance(station.get('name'), str) or not station['name'].strip(): errors.append(f'Station {index+1} needs a name.')
    layout = data.get('layout')
    if layout is not None:
        if not isinstance(layout, dict) or layout.get('shape') != 'c': errors.append('Layout must use shape c.')
        elif layout.get('break_after_station_id') is not None and (not isinstance(layout['break_after_station_id'], str) or layout['break_after_station_id'] not in ids):
            errors.append('The C-shape break must refer to a station in this setup.')
    active_ids = {s['id'] for s in source['plan']['steps'] if active_step(source['plan'], s)}
    for step_id, sid in mapping.items():
        if step_id not in active_ids: errors.append(f'Mapping refers to excluded or unknown step {step_id}.')
        if not isinstance(sid, str) or (sid and sid not in ids): errors.append(f'Step {step_id}: select a station from this setup.')
    if errors: raise ScenarioValidationError(errors)
    return data


def generate_scenario(original):
    setup = validate_setup(original)
    plan = setup['source']['plan']
    active = [s for s in plan['steps'] if active_step(plan, s)]
    by_id = {s['id']: s for s in active}
    errors = []
    if not active: errors.append('The selected case has no processes in scope.')
    if plan['takt_time'] is None: errors.append('Set takt time in the balance plan before generating a scenario.')
    assigned = {sid for op in plan['operators'] for sid in op['sequence']}
    for step in active:
        if step['id'] not in assigned: errors.append(f'{step["name"]}: assign an operator in Line Balancing.')
        if not setup['mapping'].get(step['id']): errors.append(f'{step["name"]}: map this process to a physical station.')
        if step['manual_time'] is None or step['auto_time'] is None: errors.append(f'{step["name"]}: fill both manual and automatic time in Line Balancing (use 0 if known zero).')
        elif step['manual_time'] + step['auto_time'] <= 0: errors.append(f'{step["name"]}: simulated processing needs a total time greater than zero.')
    active_ops = [(op, [sid for sid in op['sequence'] if sid in by_id]) for op in plan['operators']]
    active_ops = [(op, seq) for op, seq in active_ops if seq]
    if setup['mode'] == 'single_operator_flow' and len(active_ops) != 1:
        errors.append('Automatic transport proposal requires exactly one operator with in-scope work. Use Work steps only for multiple operators.')
    if errors: raise ScenarioValidationError(errors)
    mapping = setup['mapping']
    used = [station for station in setup['stations'] if station['id'] in set(mapping.values())]
    selected_break = (setup.get('layout') or {}).get('break_after_station_id')
    layout = c_layout([s['id'] for s in used], selected_break)
    scenario = {'schema_version': CURRENT_SCHEMA_VERSION, 'scenario_name': setup['setup_name'],
                'takt_time': plan['takt_time'], 'stations': {}, 'operators': {}, 'boxes': {}}
    for index, station in enumerate(used):
        sid = station['id']
        processes = [dict(id=s['id'], name=s['name'], manual_time=s['manual_time'], auto_time=s['auto_time'],
                         source_step_id=s['id'], source_process_id=s.get('process_id'), category=s['category'], value_class=s['value_class'])
                     for s in active if mapping[s['id']] == sid]
        scenario['stations'][sid] = {**layout['positions'][sid], 'name': station['name'], 'has_part': False, 'processes': processes, 'setup_station_id': sid}
    for index, (operator, sequence) in enumerate(active_ops):
        scenario['operators']['Op'+str(index+1)] = {'x': 240 + (index % 5)*300, 'y': 450 + (index // 5)*240,
            'name': operator['name'], 'color': COLORS[index % len(COLORS)], 'source_operator_id': operator['id'],
            'sequence': [dict(action='work', loc=mapping[sid], process=sid, source_step_id=sid) for sid in sequence]}
    scenario['boxes'] = {
        'IN_1': {**layout['input'], 'name': 'Incoming', 'type': 'in', 'start_count': setup['input_count']},
        'OUT_2': {**layout['output'], 'name': 'Outgoing', 'type': 'out', 'capacity': setup['output_capacity']}}
    if setup['mode'] == 'single_operator_flow':
        operator = scenario['operators']['Op1']; works = operator['sequence']; steps = []; previous = 'IN_1'
        for index, work in enumerate(works):
            if index == 0 or work['loc'] != works[index-1]['loc']:
                steps += [dict(action='pick', loc=previous), dict(action='drop', loc=work['loc'])]
            steps.append(work); previous = work['loc']
        steps += [dict(action='pick', loc=previous), dict(action='drop', loc='OUT_2')]
        operator['sequence'] = steps
    excluded = [s['id'] for s in plan['steps'] if s['id'] not in by_id]
    scenario['planning_origin'] = {'converter_version': 2, 'setup_snapshot': setup,
        'layout': {'shape': 'c', 'station_order': [s['id'] for s in used], 'break_after_station_id': layout['break_after_id']},
        'excluded_step_ids': excluded, 'material_review_required': True, 'review_fingerprint': None}
    scenario = validate_scenario(scenario, require_runnable=False)
    notes = ['Generated as a new unsaved scenario. Original plan, setup and scenario files are unchanged.',
             'Review positions, starting inventory, Pick/Drop handoffs, buffers and operator order in Line Builder.']
    if setup['mode'] == 'work_only': notes.append('Work-only draft: Incoming/Outgoing boxes are included; connect the material movement steps before simulation.')
    else: notes.append('Single-operator transport is a proposed serial route in that operator’s work order; review it before running.')
    if excluded: notes.append(f'{len(excluded)} excluded case/out-of-line process(es) are omitted; source IDs are retained in provenance.')
    if len(used) < len(setup['stations']): notes.append(f'{len(setup["stations"])-len(used)} unused station definition(s) are omitted.')
    if len(active_ops) < len(plan['operators']): notes.append(f'{len(plan["operators"])-len(active_ops)} operator(s) without in-scope work are omitted.')
    notes.append(f'C-shaped layout: Incoming at top right; top row runs left through S{layout["break_after_id"]}, then the lower row runs right to Outgoing.')
    if selected_break is not None and selected_break != layout['break_after_id']:
        notes.append('The saved break is no longer an interior boundary after grouping/reordering. A balanced row break is used; adjust it in the layout preview if needed.')
    return {'scenario': scenario, 'notes': notes, 'layout': layout}
