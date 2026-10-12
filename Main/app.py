"""Flask request handlers. Scenario rules and persistence live in separate modules."""
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from scenario_schema import CURRENT_SCHEMA_VERSION, EVENT_SCHEMA_VERSION, ScenarioValidationError, validate_scenario
from scenario_store import ScenarioStore, ScenarioStorageError, file_stem
from simulation import run_scenario_simulation, ScenarioRuntimeError

app = Flask(__name__)
scenario_store = ScenarioStore(Path(__file__).resolve().parent / 'scenarios')

# One latest run per server process; per-user run storage is a separate enhancement.
LAST_SIMULATION = {'events': [], 'takt_time': 30, 'scenario': None,
                   'event_schema_version': EVENT_SCHEMA_VERSION}


@app.context_processor
def template_versions():
    return {'scenario_schema_version': CURRENT_SCHEMA_VERSION,
            'event_schema_version': EVENT_SCHEMA_VERSION}


@app.errorhandler(ScenarioValidationError)
def validation_error(exc):
    return jsonify(status='invalid', errors=exc.errors, error='\n'.join(exc.errors)), 400


@app.errorhandler(ScenarioStorageError)
def storage_error(exc):
    return jsonify(status=exc.status, error=str(exc), **exc.details), exc.code


@app.route('/')
@app.route('/builder')
def builder():
    return render_template('builder.html')


@app.route('/simulate')
def simulate():
    return render_template('simulate.html')


@app.route('/launch', methods=['POST'])
def launch():
    global LAST_SIMULATION
    scenario = validate_scenario(request.get_json(silent=True))
    try:
        events, takt_time = run_scenario_simulation(scenario)
    except ScenarioRuntimeError as exc:
        return jsonify(status='runtime_error', error=str(exc)), 400
    LAST_SIMULATION = {'events': events, 'takt_time': takt_time, 'scenario': scenario,
                       'event_schema_version': EVENT_SCHEMA_VERSION}
    return jsonify(status='ok')


@app.route('/events')
def get_events():
    return jsonify(LAST_SIMULATION)


@app.route('/save-scenario', methods=['POST'])
def save_scenario():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ScenarioStorageError('invalid', 'Scenario data is required.')
    result = scenario_store.save(payload.get('filename') or payload.get('name', 'untitled'),
                                 payload.get('scenario'), payload.get('mode', 'create'),
                                 payload.get('expected_revision'))
    return jsonify(result)


@app.route('/list-scenarios')
def list_scenarios():
    return jsonify(files=scenario_store.list_files())


@app.route('/load-scenario/<filename>')
def load_scenario(filename):
    return jsonify(scenario_store.load(filename))


@app.route('/delete-scenario/<filename>', methods=['POST'])
def delete_scenario(filename):
    return jsonify(scenario_store.delete(filename))


@app.route('/import-scenario', methods=['POST'])
def import_scenario():
    payload = request.get_json(silent=True)
    original = payload.get('scenario') if isinstance(payload, dict) else None
    scenario = validate_scenario(original, require_runnable=False)
    source_version = original.get('schema_version', 1)
    return jsonify(status='imported', scenario=scenario,
                   migrated_from=source_version if source_version != CURRENT_SCHEMA_VERSION else None)


@app.route('/export-scenario', methods=['POST'])
def export_scenario():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ScenarioStorageError('invalid', 'Scenario data is required.')
    scenario = validate_scenario(payload.get('scenario'), require_runnable=False)
    filename = file_stem(payload.get('filename') or 'scenario') + '.json'
    response = jsonify(scenario)
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
