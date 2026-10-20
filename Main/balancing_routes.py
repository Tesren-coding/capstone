"""Line balancing is its own app; source selection copies PQPR data."""
from pathlib import Path
from flask import Blueprint, jsonify, render_template, request
from balancing_schema import BALANCING_SCHEMA_VERSION, validate_plan, plan_from_pqpr, analyse_plan
from balancing_store import BalancingStore
from storage_factory import make_store
from scenario_schema import ScenarioValidationError
from scenario_store import file_stem

balancing = Blueprint('balancing', __name__, url_prefix='/line-balancing')
balancing_store = make_store('balancing', Path(__file__).resolve().parent / 'balancing_plans',
                             BalancingStore, validate_plan, 'plan')


def payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ScenarioValidationError(['Balancing plan data is required.'])
    return data


@balancing.get('')
def editor():
    return render_template('balancing.html', page_title='Line Balancing', active_module='line-balancing', balancing_schema_version=BALANCING_SCHEMA_VERSION)


@balancing.post('/api/from-pqpr')
def from_pqpr():
    data = payload()
    plan = plan_from_pqpr(data.get('project'), data.get('framesize_id'), data.get('filename'), data.get('revision'))
    return jsonify(plan=plan, analysis=analyse_plan(plan))


@balancing.get('/api/plans')
def list_plans():
    return jsonify(files=balancing_store.list_files())


@balancing.get('/api/plans/<filename>')
def load_plan(filename):
    return jsonify(balancing_store.load(filename))


@balancing.post('/api/save')
def save_plan():
    data = payload()
    return jsonify(balancing_store.save(data.get('filename') or data.get('name', 'untitled'), data.get('plan'), data.get('mode', 'create'), data.get('expected_revision')))


@balancing.post('/api/import')
def import_plan():
    plan = validate_plan(payload().get('plan'))
    return jsonify(plan=plan, analysis=analyse_plan(plan))


@balancing.post('/api/export')
def export_plan():
    data = payload()
    plan = validate_plan(data.get('plan'))
    response = jsonify(plan)
    response.headers['Content-Disposition'] = f'attachment; filename="{file_stem(data.get("filename") or plan["plan_name"])}.json"'
    return response


@balancing.post('/api/analyse')
def analyse():
    return jsonify(analysis=analyse_plan(validate_plan(payload().get('plan'))))
