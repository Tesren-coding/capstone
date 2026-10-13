"""Matrix timing migration and process/working-element planning workflows."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from pqpr_schema import validate_pqpr, frame_totals
from pqpr_store import PQPRStore
from balancing_schema import plan_from_pqpr, validate_plan, analyse_plan
from builder_setup import setup_from_plan, generate_scenario
from scenario_schema import ScenarioValidationError, review_planning_scenario
from simulation import run_scenario_simulation
from test_pqpr import project as old_project
from test_balancing import complete_plan


def matrix_project():
    project=validate_pqpr(old_project())
    project['framesizes'][0]['parts_per_set']=12
    project['framesizes'][0]['timings']['p1']={'manual_time':4,'auto_time':2}
    project['framesizes'][1]['timings']['p1']={'manual_time':8,'auto_time':3}
    return project


def broken_down_plan():
    project=matrix_project()
    plan=plan_from_pqpr(project,'f1')
    plan['steps']=[dict(id='s'+str(i+1),balance_process_id='p1',process_id='p1',name=name,
                        category='in_line',applicability='required',included=True,
                        manual_time=manual,auto_time=automatic,value_class='va')
                   for i,(name,manual,automatic) in enumerate([('Load',1,0),('Inspect',2,2),('Unload',1,0)])]
    plan['operators']=[{'id':'o1','name':'Alice','sequence':['s1','s2','s3']}]
    plan['next_step_id']=4;plan['next_operator_id']=2
    return validate_plan(plan)


class MatrixTimingTests(unittest.TestCase):
    def test_old_cells_keep_membership_and_independent_copies(self):
        original=old_project();before=deepcopy(original);data=validate_pqpr(original)
        self.assertEqual(original,before)
        self.assertEqual(data['schema_version'],2)
        for frame in data['framesizes']:
            self.assertEqual(frame['parts_per_set'],1)
            self.assertEqual(set(frame['timings']),set(frame['applicability']))
        data['framesizes'][0]['timings']['p1']['manual_time']=7
        self.assertEqual(data['framesizes'][1]['timings']['p1']['manual_time'],.5)
        self.assertEqual(data['processes'][0]['manual_time'],.5)

    def test_row_totals_use_cell_times_and_are_per_part(self):
        data=matrix_project()
        self.assertEqual(frame_totals(data,data['framesizes'][0]),{'process_count':2,'optional_count':1,'manual_time':5,'auto_time':22})
        data['framesizes'][1]['timings']['p3']={'manual_time':0,'auto_time':0}
        self.assertEqual(frame_totals(data,data['framesizes'][1])['manual_time'],8)
        self.assertEqual(validate_pqpr(data),data)

    def test_invalid_quantities_cell_references_and_times_fail(self):
        invalid=[]
        for quantity in [0,-1,1.5,True,None,'12']:
            data=matrix_project();data['framesizes'][0]['parts_per_set']=quantity;invalid.append(data)
        for timing in [{'manual_time':-1,'auto_time':0},{'manual_time':True,'auto_time':0},{'auto_time':1},[]]:
            data=matrix_project();data['framesizes'][0]['timings']['p1']=timing;invalid.append(data)
        data=matrix_project();data['framesizes'][0]['timings']['p3']={'manual_time':0,'auto_time':0};invalid.append(data)
        data=matrix_project();del data['framesizes'][0]['timings']['p1'];invalid.append(data)
        data=old_project();data['processes'][0]['id']=[];invalid.append(data)
        for data in invalid:
            with self.subTest(data=data),self.assertRaises(ScenarioValidationError):validate_pqpr(data)

    def test_load_old_file_does_not_rewrite_and_new_cells_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory,'old.json');target.write_text(json.dumps(old_project()));before=target.read_bytes()
            store=PQPRStore(directory);loaded=store.load('old.json')['project']
            self.assertEqual(target.read_bytes(),before)
            loaded['framesizes'][0]['parts_per_set']=8
            loaded['framesizes'][0]['timings']['p1']['manual_time']=3
            store.save('old',loaded,'duplicate')
            self.assertEqual(store.load('old_v2.json')['project'],loaded)
            self.assertEqual(target.read_bytes(),before)


class WorkingElementTests(unittest.TestCase):
    def test_pqpr_import_creates_processes_with_framesize_times_only(self):
        source=matrix_project();before=deepcopy(source);plan=plan_from_pqpr(source,'f1')
        self.assertEqual(plan['steps'],[])
        self.assertEqual(plan['parts_per_set'],12)
        self.assertEqual([p['id'] for p in plan['processes']],['p1','p2'])
        self.assertEqual(plan['processes'][0]['manual_time'],4)
        self.assertEqual(plan['processes'][0]['auto_time'],2)
        self.assertEqual(analyse_plan(plan)['processes_without_elements'],['p1'])
        self.assertIsNone(analyse_plan(plan)['manual_total'])
        plan['processes'][0]['manual_time']=99
        self.assertEqual(source,before)
        self.assertEqual(plan_from_pqpr(source,'f2')['processes'][0]['manual_time'],8)

    def test_parent_reference_times_are_not_double_counted(self):
        plan=broken_down_plan();plan['processes'][0]['manual_time']=100
        result=analyse_plan(plan)
        self.assertEqual(result['manual_total'],4)
        self.assertEqual(result['operators'][0]['manual_time'],4)
        self.assertEqual(result['operators'][0]['auto_time'],2)
        self.assertEqual(result['processes_without_elements'],[])
        self.assertEqual(result['balance_efficiency'],100)

    def test_multiple_elements_group_to_one_physical_station(self):
        plan=broken_down_plan();setup=setup_from_plan(plan)
        self.assertEqual(len(setup['stations']),1)
        self.assertEqual(set(setup['mapping'].values()),{'1'})
        setup['mode']='single_operator_flow';scene=generate_scenario(setup)['scenario']
        self.assertEqual(scene['parts_per_set'],12)
        self.assertEqual([p['name'] for p in scene['stations']['1']['processes']],['Load','Inspect','Unload'])
        events,_=run_scenario_simulation(review_planning_scenario(scene))
        self.assertTrue(any(e['status']=='dropoff' and e['loc']=='OUT_2' for e in events))
        self.assertFalse(any(e['status']=='blocked' for e in events))

    def test_unbroken_process_cannot_silently_disappear_from_generation(self):
        plan=broken_down_plan();plan['include_out_of_line']=True
        self.assertEqual(analyse_plan(plan)['processes_without_elements'],['p2'])
        self.assertIsNone(analyse_plan(plan)['balance_efficiency'])
        with self.assertRaisesRegex(ScenarioValidationError,'working elements'):
            generate_scenario(setup_from_plan(plan))

    def test_parent_scope_and_bad_references(self):
        plan=broken_down_plan();plan['processes'][0].update(applicability='optional',included=False)
        self.assertEqual(analyse_plan(plan)['active_steps'],0)
        plan['steps'][0]['balance_process_id']='missing'
        with self.assertRaisesRegex(ScenarioValidationError,'parent process'):validate_plan(plan)
        plan=broken_down_plan();plan['line_layout']={'shape':'c','break_after_process_id':'missing'}
        with self.assertRaises(ScenarioValidationError):validate_plan(plan)

    def test_old_plan_migration_preserves_work_ids_assignments_and_break(self):
        for version in [1,2]:
            old=complete_plan();old['schema_version']=version
            old.pop('processes');old.pop('next_process_id');old.pop('parts_per_set')
            for step in old['steps']:step.pop('balance_process_id')
            old['line_layout']={'shape':'c','break_after_step_id':'p1'}
            if version==1:old.pop('next_step_id')
            before=deepcopy(old);new=validate_plan(old)
            self.assertEqual(old,before)
            self.assertEqual(new['schema_version'],3)
            self.assertEqual(new['operators'],old['operators'])
            self.assertEqual([s['id'] for s in new['steps']],[s['id'] for s in old['steps']])
            self.assertEqual(new['line_layout']['break_after_process_id'],'bp1')
            self.assertEqual(validate_plan(new),new)


if __name__=='__main__':unittest.main()
