"""Dashboard and module entry pages. Planning tools are added in stages."""
from flask import Blueprint, render_template

planning = Blueprint('planning', __name__)

# One registry drives dashboard cards and shared navigation.
MODULES = [
    {'id': 'pqpr', 'title': 'PQPR', 'icon': 'PQ',
     'description': 'List the processes each product framesize needs to go through.',
     'status': 'development', 'endpoint': 'pqpr.editor',
     'features': ['Product framesizes', 'Ordered process routes', 'Process counts']},
    {'id': 'line-balancing', 'title': 'Line Balancing', 'icon': 'LB',
     'description': 'Assign processes to operators and compare their workloads against takt time.',
     'status': 'development', 'endpoint': 'balancing.editor',
     'features': ['Independent process steps', 'Operator assignments', 'Draggable workload charts']},
    {'id': 'line-builder', 'title': 'Line Builder', 'icon': 'LN',
     'description': 'Arrange stations, define operator sequences and simulate material flow.',
     'status': 'available', 'endpoint': 'builder',
     'features': ['Station layout', 'Manual and automatic time', 'Simulation playback']},
]


@planning.route('/')
@planning.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', page_title='Dashboard',
                           active_module='dashboard', modules=MODULES)


def planned_module(module_id):
    module = next(item for item in MODULES if item['id'] == module_id)
    return render_template('module_planned.html', page_title=module['title'],
                           active_module=module_id, module=module)


