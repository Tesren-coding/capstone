"""Standalone balance format 2, with migration from PQPR-bound format 1."""
from copy import deepcopy
import json
import math
import re
from pqpr_schema import validate_pqpr
from scenario_schema import ScenarioValidationError

BALANCING_SCHEMA_VERSION = 2
VALUE_CLASSES = ('unclassified', 'va', 'sva', 'nva')


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def blank_plan():
    return {'document_type': 'line_balance', 'schema_version': BALANCING_SCHEMA_VERSION,
            'plan_name': 'New balance plan', 'takt_time': 30,
            'source': None, 'framesize_id': None, 'steps': [], 'operators': [],
            'next_operator_id': 1, 'next_step_id': 1, 'chart_color_mode': 'process', 'include_out_of_line': False}


def plan_from_pqpr(project, framesize_id, filename=None, revision=None):
    project = validate_pqpr(project)
    frame = next((f for f in project['framesizes'] if f['id'] == framesize_id), None)
    if frame is None:
        raise ScenarioValidationError(['Select a valid framesize from the PQPR project.'])
    plan = blank_plan()
    suffix = ' / Stage ' + frame['stage'] if frame['stage'] else ''
    plan['plan_name'] = project['project_name'] + ' — ' + frame['name'] + suffix
    plan['source'] = {'project': project, 'filename': filename, 'revision': revision}
    plan['framesize_id'] = framesize_id
    plan['steps'] = [dict(id=p['id'], process_id=p['id'], name=p['name'], category=p['category'],
                         applicability=frame['applicability'][p['id']], included=True,
                         manual_time=p['manual_time'], auto_time=p['auto_time'], value_class='unclassified')
                     for p in project['processes'] if p['id'] in frame['applicability']]
    return validate_plan(plan)


def validate_plan(original):
    if not isinstance(original, dict) or original.get('document_type') != 'line_balance':
        raise ScenarioValidationError(['Choose a line-balancing plan JSON file. PQPR data is loaded through the source selector.'])
    version = original.get('schema_version')
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ScenarioValidationError(['Balancing schema_version must be a positive integer.'])
    if version > BALANCING_SCHEMA_VERSION:
        raise ScenarioValidationError([f'Balancing format v{version} is newer than this app supports (v{BALANCING_SCHEMA_VERSION}). Update the app.'])
    legacy = version == 1
    plan = deepcopy(original)
    try:
        json.dumps(plan, allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise ScenarioValidationError(['A balancing plan must contain valid JSON and finite numbers.']) from exc
    errors = []
    if not isinstance(plan.get('plan_name'), str) or not plan['plan_name'].strip():
        errors.append('Name the balancing plan.')
    takt = plan.get('takt_time')
    if 'takt_time' not in plan or (takt is not None and (not number(takt) or takt <= 0)):
        errors.append('Takt time must be positive minutes, or null while unknown.')
    if plan.get('chart_color_mode') not in ('process', 'value'):
        errors.append('Chart color mode must be process or value.')
    if not isinstance(plan.get('include_out_of_line'), bool):
        errors.append('include_out_of_line must be true or false.')
    for key in ('steps', 'operators'):
        if not isinstance(plan.get(key), list):
            errors.append(f'{key} must be a list.')
    counter = plan.get('next_operator_id', 1)
    if not isinstance(counter, int) or isinstance(counter, bool) or counter < 1:
        errors.append('next_operator_id must be a positive integer.')
    if errors:
        raise ScenarioValidationError(errors)
    source = plan.get('source')
    source_processes, expected_route = {}, None
    if source is None:
        if (legacy and plan['steps']) or plan.get('framesize_id') is not None:
            errors.append('A plan with process steps needs a PQPR source and selected framesize.')
    elif not isinstance(source, dict):
        errors.append('Source must be a PQPR copy or null in an empty draft.')
    else:
        project = validate_pqpr(source.get('project'))
        source['project'] = project
        frame = next((f for f in project['framesizes'] if f['id'] == plan.get('framesize_id')), None)
        if frame is None:
            errors.append('The selected framesize does not exist in the copied PQPR project.')
        else:
            expected_route = frame['applicability']
        source_processes = {p['id']: p for p in project['processes']}
        for key in ('filename', 'revision'):
            if source.get(key) is not None and not isinstance(source[key], str):
                errors.append(f'Source {key} must be text or null.')

    def valid_id(identifier):
        return isinstance(identifier, str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', identifier) and identifier not in ('__proto__', 'constructor', 'prototype')

    step_ids, process_ids = set(), set()
    for index, step in enumerate(plan['steps']):
        label = f'Step {index+1}'
        if not isinstance(step, dict):
            errors.append(f'{label} must be an object.')
            continue
        if not valid_id(step.get('id')) or step['id'] in step_ids:
            errors.append(f'{label} needs a unique stable ID.')
        else:
            step_ids.add(step['id'])
        pid = step.get('process_id')
        if legacy and (not isinstance(pid, str) or pid not in source_processes or pid in process_ids):
            errors.append(f'{label} needs a unique process reference from its PQPR route.')
        elif pid is not None and not valid_id(pid):
            errors.append(f'{label} has an invalid source process ID.')
        elif isinstance(pid, str):
            process_ids.add(pid)
        if legacy and expected_route is not None and isinstance(pid, str) and (pid not in expected_route or step.get('applicability') != expected_route.get(pid)):
            errors.append(f'{label}: applicability must match the selected PQPR route.')
        if not isinstance(step.get('name'), str) or not step['name'].strip():
            errors.append(f'{label} needs a name.')
        if step.get('category') not in ('in_line', 'out_of_line', 'unique'):
            errors.append(f'{label} has an invalid process category.')
        if step.get('applicability') not in ('required', 'optional'):
            errors.append(f'{label} has invalid applicability.')
        if not isinstance(step.get('included'), bool) or (step.get('applicability') == 'required' and not step.get('included')):
            errors.append(f'{label}: Always steps must remain included; Sometimes steps may be excluded.')
        if step.get('value_class') not in VALUE_CLASSES:
            errors.append(f'{label} needs a valid value-add classification.')
        for key in ('manual_time', 'auto_time'):
            if key not in step or (step[key] is not None and not number(step[key])):
                errors.append(f'{label}: {key} must be nonnegative minutes or null when unknown.')
    if legacy and expected_route is not None and process_ids != set(expected_route):
        errors.append('The plan must retain every process from the selected PQPR route.')
    operator_ids, assigned = set(), set()
    for index, operator in enumerate(plan['operators']):
        label = f'Operator {index+1}'
        if not isinstance(operator, dict):
            errors.append(f'{label} must be an object.')
            continue
        if not valid_id(operator.get('id')) or operator['id'] in operator_ids:
            errors.append(f'{label} needs a unique stable ID.')
        else:
            operator_ids.add(operator['id'])
        if not isinstance(operator.get('name'), str) or not operator['name'].strip():
            errors.append(f'{label} needs a name.')
        sequence = operator.get('sequence')
        if not isinstance(sequence, list):
            errors.append(f'{label} needs a sequence list.')
            continue
        for identifier in sequence:
            if not isinstance(identifier, str) or identifier not in step_ids:
                errors.append(f'{label} refers to an unknown step.')
            elif identifier in assigned:
                errors.append(f'Step {identifier} is assigned more than once. Each step can have one operator.')
            else:
                assigned.add(identifier)
    layout = plan.get('line_layout')
    if layout is not None:
        if not isinstance(layout, dict) or layout.get('shape') != 'c':
            errors.append('line_layout must use shape c.')
        elif layout.get('break_after_step_id') is not None and (not isinstance(layout['break_after_step_id'], str) or layout['break_after_step_id'] not in step_ids):
            errors.append('The C-shape break must refer to a process step in this plan.')
    if not legacy:
        step_counter = plan.get('next_step_id')
        if not isinstance(step_counter, int) or isinstance(step_counter, bool) or step_counter < 1:
            errors.append('next_step_id must be a positive integer.')
    if errors:
        raise ScenarioValidationError(errors)
    if legacy:
        plan['schema_version'] = BALANCING_SCHEMA_VERSION
        plan['next_step_id'] = max([int(sid[1:]) for sid in step_ids if re.fullmatch(r's[0-9]+', sid)] + [0]) + 1
    plan.setdefault('next_operator_id', 1)
    return plan


def active_step(plan, step):
    return step['included'] and (plan['include_out_of_line'] or step['category'] != 'out_of_line')


def analyse_plan(plan):
    active = [step for step in plan['steps'] if active_step(plan, step)]
    by_id = {step['id']: step for step in plan['steps']}
    assigned = {sid for operator in plan['operators'] for sid in operator['sequence']}
    total_manual = None if any(s['manual_time'] is None for s in active) else sum(s['manual_time'] for s in active)
    operators = []
    for operator in plan['operators']:
        steps = [by_id[sid] for sid in operator['sequence'] if active_step(plan, by_id[sid])]
        manual = None if any(s['manual_time'] is None for s in steps) else sum(s['manual_time'] for s in steps)
        automatic = None if any(s['auto_time'] is None for s in steps) else sum(s['auto_time'] for s in steps)
        takt = plan['takt_time']
        status = 'no_steps' if not steps else 'incomplete' if manual is None or takt is None else 'over_takt' if manual > takt + 1e-9 else 'within_takt'
        operators.append({'id': operator['id'], 'name': operator['name'], 'step_count': len(steps),
                          'manual_time': manual, 'known_manual_time': sum(s['manual_time'] or 0 for s in steps),
                          'auto_time': automatic, 'utilization': manual/takt*100 if manual is not None and takt else None, 'status': status})
    unassigned = [s['id'] for s in active if s['id'] not in assigned]
    complete = not unassigned and total_manual is not None and bool(operators) and bool(active)
    maximum = max((op['manual_time'] for op in operators), default=0) if complete else None
    ratio = total_manual/plan['takt_time'] if total_manual is not None and plan['takt_time'] else None
    # Avoid an extra operator from binary rounding (e.g. (0.1 + 0.2) / 0.1).
    minimum = max(1, math.ceil(ratio - 4*math.ulp(1.0)*ratio)) if ratio else 0 if ratio == 0 else None
    return {'active_steps': len(active), 'unassigned': unassigned,
            'unknown_manual': [s['id'] for s in active if s['manual_time'] is None],
            'unknown_auto': [s['id'] for s in active if s['auto_time'] is None],
            'manual_total': total_manual,
            'known_manual_total': sum(s['manual_time'] or 0 for s in active),
            'operators': operators,
            'minimum_operators': minimum,
            'balance_efficiency': total_manual/(len(operators)*maximum)*100 if complete and maximum else None,
            'takt_load': total_manual/(len(operators)*plan['takt_time'])*100 if complete and plan['takt_time'] else None}
