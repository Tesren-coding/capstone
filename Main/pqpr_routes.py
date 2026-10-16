"""PQPR app HTTP endpoints; saved projects are separate from line scenarios."""
from pathlib import Path
from flask import Blueprint, jsonify, render_template, request
from pqpr_schema import PQPR_SCHEMA_VERSION, validate_pqpr
from pqpr_store import PQPRStore
from storage_factory import make_store
from pqpr_excel import worksheets, import_worksheet
from scenario_schema import ScenarioValidationError
from scenario_store import file_stem, ScenarioStorageError

pqpr = Blueprint('pqpr', __name__, url_prefix='/pqpr')
pqpr_store = make_store('pqpr', Path(__file__).resolve().parent / 'pqpr_projects',
                        PQPRStore, validate_pqpr, 'project')


@pqpr.route('')
def editor():
    return render_template('pqpr.html', page_title='PQPR', active_module='pqpr', pqpr_schema_version=PQPR_SCHEMA_VERSION)


def payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ScenarioValidationError(['PQPR project data is required.'])
    return data


@pqpr.get('/api/projects')
def list_projects():
    return jsonify(files=pqpr_store.list_files())


@pqpr.get('/api/projects/<filename>')
def load_project(filename):
    return jsonify(pqpr_store.load(filename))


@pqpr.post('/api/save')
def save_project():
    data = payload()
    return jsonify(pqpr_store.save(data.get('filename') or data.get('name', 'untitled'), data.get('project'),
                                   data.get('mode', 'create'), data.get('expected_revision')))


@pqpr.post('/api/import')
def import_project():
    return jsonify(status='imported', project=validate_pqpr(payload().get('project')))


@pqpr.post('/api/export')
def export_project():
    data = payload()
    project = validate_pqpr(data.get('project'))
    response = jsonify(project)
    response.headers['Content-Disposition'] = f'attachment; filename="{file_stem(data.get("filename") or project["project_name"])}.json"'
    return response


@pqpr.post('/api/import-excel')
def import_excel():
    file = request.files.get('file')
    if file is None or not file.filename.lower().endswith('.xlsx'):
        raise ScenarioValidationError(['Choose an .xlsx PQPR workbook.'])
    raw = file.read()
    choices = worksheets(raw)
    name = request.form.get('worksheet')
    if not name and len(choices) > 1:
        return jsonify(status='choose_sheet', worksheets=choices)
    project, warnings = import_worksheet(raw, name or choices[0]['name'], file.filename)
    return jsonify(status='imported', project=project, warnings=warnings)
