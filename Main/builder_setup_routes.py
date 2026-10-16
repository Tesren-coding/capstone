"""Stage 4 setup editor, validated conversion and explicit builder review."""
from pathlib import Path
from flask import Blueprint, jsonify, render_template, request
from builder_setup import SETUP_SCHEMA_VERSION, setup_from_plan, validate_setup, generate_scenario
from scenario_store import ScenarioStore, file_stem
from storage_factory import make_store
from scenario_schema import ScenarioValidationError, validate_scenario, planning_review_required, planning_reviewed, review_planning_scenario

bridge = Blueprint('bridge', __name__, url_prefix='/builder-setup')


class SetupStore(ScenarioStore):
    def __init__(self, directory): super().__init__(directory, normalizer=validate_setup)
    def load(self, name):
        result = super().load(name); result['setup'] = result.pop('scenario'); return result


setup_store = make_store('builder_setup', Path(__file__).resolve().parent / 'builder_setups',
                         SetupStore, validate_setup, 'setup')


def payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict): raise ScenarioValidationError(['Setup data is required.'])
    return data


@bridge.get('')
def editor():
    return render_template('builder_setup.html', page_title='Build a line from a balance plan', active_module='line-builder', setup_schema_version=SETUP_SCHEMA_VERSION)


@bridge.post('/api/from-plan')
def from_plan():
    data = payload(); return jsonify(setup=setup_from_plan(data.get('plan'), data.get('filename'), data.get('revision')))


@bridge.get('/api/setups')
def list_setups(): return jsonify(files=setup_store.list_files())


@bridge.get('/api/setups/<filename>')
def load_setup(filename): return jsonify(setup_store.load(filename))


@bridge.post('/api/save')
def save_setup():
    data = payload(); return jsonify(setup_store.save(data.get('filename') or data.get('name', 'untitled'), data.get('setup'), data.get('mode', 'create'), data.get('expected_revision')))


@bridge.post('/api/import')
def import_setup(): return jsonify(setup=validate_setup(payload().get('setup')))


@bridge.post('/api/export')
def export_setup():
    data = payload(); setup = validate_setup(data.get('setup')); response = jsonify(setup)
    response.headers['Content-Disposition'] = f'attachment; filename="{file_stem(setup["setup_name"])}.json"'; return response


@bridge.post('/api/generate')
def generate(): return jsonify(generate_scenario(payload().get('setup')))


@bridge.post('/api/review-status')
def review_status():
    data = validate_scenario(payload().get('scenario'), require_runnable=False)
    return jsonify(required=planning_review_required(data), reviewed=planning_reviewed(data))


@bridge.post('/api/review')
def review(): return jsonify(scenario=review_planning_scenario(payload().get('scenario')))
