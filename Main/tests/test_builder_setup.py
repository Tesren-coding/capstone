"""Stage 4 ownership, mapping, movement proposal and review regressions."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
import app as web
import builder_setup_routes as routes
from builder_setup import setup_from_plan, validate_setup, generate_scenario
from balancing_schema import blank_plan
from scenario_schema import ScenarioValidationError, validate_scenario, planning_reviewed, review_planning_scenario
from simulation import run_scenario_simulation


def plan_fixture(two_operators=False):
    plan = blank_plan(); plan['plan_name'] = 'Assembly'; plan['takt_time'] = 30
    plan['steps'] = [dict(id='s'+str(i+1),process_id=None,name=name,category='in_line',applicability='required',included=True,manual_time=manual,auto_time=automatic,value_class='va')
                     for i,(name,manual,automatic) in enumerate([('Inspect',1,2),('Blend',2,0),('Pack',1,0)])]
    plan['next_step_id'] = 4
    plan['operators'] = [dict(id='o1',name='Alice',sequence=['s1','s2','s3'])]
    if two_operators:
        plan['operators'][0]['sequence'] = ['s2','s1']
        plan['operators'].append(dict(id='o2',name='Bob',sequence=['s3']))
    plan['next_operator_id'] = 3
    plan['notes'] = {'owner':'Example'}
    return plan


class SetupTests(unittest.TestCase):
    def test_mapping_groups_steps_and_preserves_work_order_times_and_source(self):
        original = plan_fixture(True); before = deepcopy(original)
        setup = setup_from_plan(original,'balance.json','revision')
        setup['mapping']['s2'] = '1'
        result = generate_scenario(setup); scenario = result['scenario']
        self.assertEqual(list(scenario['stations']),['1','3'])
        self.assertEqual([p['id'] for p in scenario['stations']['1']['processes']],['s1','s2'])
        self.assertEqual(scenario['stations']['1']['processes'][0]['auto_time'],2)
        self.assertEqual(scenario['operators']['Op1']['name'],'Op1')
        self.assertEqual([s['process'] for s in scenario['operators']['Op1']['sequence']],['s2','s1'])
        self.assertEqual(scenario['operators']['Op2']['sequence'][0]['loc'],'3')
        self.assertEqual(scenario['planning_origin']['setup_snapshot']['source']['filename'],'balance.json')
        self.assertEqual(scenario['planning_origin']['setup_snapshot']['source']['plan']['notes'],original['notes'])
        self.assertEqual(original,before)
        self.assertEqual(scenario['schema_version'],2)
        self.assertFalse(planning_reviewed(scenario))

    def test_single_operator_proposal_keeps_consecutive_shared_station_work_together(self):
        setup = setup_from_plan(plan_fixture()); setup['mode'] = 'single_operator_flow'
        setup['mapping']['s2'] = '1'
        scenario = generate_scenario(setup)['scenario']
        self.assertEqual([(s['action'],s['loc']) for s in scenario['operators']['Op1']['sequence']],
            [('pick','IN_1'),('drop','1'),('work','1'),('work','1'),('pick','1'),('drop','3'),('work','3'),('pick','3'),('drop','OUT_2')])
        self.assertEqual(scenario['boxes']['IN_1']['start_count'],150)
        with self.assertRaises(ScenarioValidationError): validate_scenario(scenario)
        reviewed = review_planning_scenario(scenario)
        self.assertTrue(planning_reviewed(reviewed))
        events,_ = run_scenario_simulation(reviewed)
        self.assertFalse(any(e['status']=='blocked' for e in events))
        self.assertTrue(any(e['status']=='dropoff' and e['loc']=='OUT_2' for e in events))
        self.assertEqual([p['source_step_id'] for s in reviewed['stations'].values() for p in s['processes']],['s1','s2','s3'])

    def test_revisiting_one_station_generates_an_explicit_return(self):
        setup = setup_from_plan(plan_fixture()); setup['mode'] = 'single_operator_flow'; setup['mapping']['s3']='1'
        scenario = generate_scenario(setup)['scenario']
        self.assertEqual([s['loc'] for s in scenario['operators']['Op1']['sequence'] if s['action']=='drop'],['1','2','1','OUT_2'])
        reviewed = review_planning_scenario(scenario)
        events,_ = run_scenario_simulation(reviewed)
        self.assertFalse(any(e['status']=='blocked' for e in events))

    def test_scope_omissions_do_not_lose_source_or_create_empty_operators(self):
        plan = plan_fixture(True)
        plan['steps'][2]['category']='out_of_line'
        plan['steps'].append(dict(id='s4',process_id=None,name='Optional',category='in_line',applicability='optional',included=False,manual_time=None,auto_time=None,value_class='unclassified'))
        scenario = generate_scenario(setup_from_plan(plan))['scenario']
        self.assertEqual(len(scenario['stations']),2);self.assertEqual(len(scenario['operators']),1)
        self.assertEqual(scenario['planning_origin']['excluded_step_ids'],['s3','s4'])
        self.assertEqual(len(scenario['planning_origin']['setup_snapshot']['source']['plan']['steps']),4)

    def test_generation_rejects_unknown_zero_unassigned_unmapped_and_multioperator_transport(self):
        bad=[]
        setup=setup_from_plan(plan_fixture());setup['source']['plan']['steps'][0]['auto_time']=None;bad.append(setup)
        setup=setup_from_plan(plan_fixture());setup['source']['plan']['steps'][0].update(manual_time=0,auto_time=0);bad.append(setup)
        setup=setup_from_plan(plan_fixture());setup['source']['plan']['operators'][0]['sequence'].remove('s1');bad.append(setup)
        setup=setup_from_plan(plan_fixture());setup['mapping']['s1']='';bad.append(setup)
        setup=setup_from_plan(plan_fixture());setup['source']['plan']['takt_time']=None;bad.append(setup)
        setup=setup_from_plan(plan_fixture(True));setup['mode']='single_operator_flow';bad.append(setup)
        for setup in bad:
            with self.subTest(setup=setup), self.assertRaises(ScenarioValidationError):generate_scenario(setup)
        self.assertEqual(validate_setup(bad[3]),bad[3]) # Mapping drafts can be saved.

    def test_setup_rejects_invalid_versions_station_ids_and_mapping_references(self):
        bad=[]
        for version in [2,True,0,'1']:
            setup=setup_from_plan(plan_fixture());setup['schema_version']=version;bad.append(setup)
        for sid in ['0','01','constructor','9007199254740992']:
            setup=setup_from_plan(plan_fixture());setup['stations'][0]['id']=sid;bad.append(setup)
        setup=setup_from_plan(plan_fixture());setup['mapping']['missing']='1';bad.append(setup)
        setup=setup_from_plan(plan_fixture());setup['mapping']['s1']='99';bad.append(setup)
        setup=setup_from_plan(plan_fixture());setup['stations'][1]['id']='1';bad.append(setup)
        for setup in bad:
            with self.subTest(setup=setup),self.assertRaises(ScenarioValidationError):validate_setup(setup)

    def test_work_only_cannot_be_reviewed_without_material_parts_or_deliveries(self):
        scenario=generate_scenario(setup_from_plan(plan_fixture()))['scenario']
        validate_scenario(scenario,require_runnable=False)
        with self.assertRaises(ScenarioValidationError):review_planning_scenario(scenario)
        for station in scenario['stations'].values():station['has_part']=True
        self.assertTrue(planning_reviewed(review_planning_scenario(scenario)))

    def test_review_is_invalidated_by_core_edits_but_not_provenance_notes(self):
        setup=setup_from_plan(plan_fixture());setup['mode']='single_operator_flow'
        reviewed=review_planning_scenario(generate_scenario(setup)['scenario'])
        reviewed['planning_origin']['comment']='Review note';self.assertTrue(planning_reviewed(reviewed))
        mutations=[lambda s:s['stations']['1'].update(x=600),lambda s:s['stations']['1']['processes'][0].update(manual_time=2),
            lambda s:s['operators']['Op1']['sequence'].pop(),lambda s:s['boxes']['IN_1'].update(start_count=2),lambda s:s.update(takt_time=20)]
        for mutate in mutations:
            changed=deepcopy(reviewed);mutate(changed)
            self.assertFalse(planning_reviewed(changed))
            with self.assertRaises(ScenarioValidationError):validate_scenario(changed)
            validate_scenario(changed,require_runnable=False)


class SetupRoutesTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.previous=routes.setup_store
        routes.setup_store=routes.SetupStore(self.temporary.name);self.client=web.app.test_client()
    def tearDown(self):routes.setup_store=self.previous;self.temporary.cleanup()

    def test_mapping_storage_roundtrip_versions_conflict_and_preview_does_not_save(self):
        setup=self.client.post('/builder-setup/api/from-plan',json={'plan':plan_fixture()}).get_json()['setup']
        self.assertEqual(self.client.get('/builder-setup').status_code,200)
        result=self.client.post('/builder-setup/api/generate',json={'setup':setup});self.assertEqual(result.status_code,200)
        self.assertEqual(routes.setup_store.list_files(),[])
        saved=self.client.post('/builder-setup/api/save',json={'setup':setup,'name':'mapping'}).get_json()
        original=Path(self.temporary.name,'mapping.json').read_bytes()
        loaded=self.client.get('/builder-setup/api/setups/mapping.json').get_json();self.assertEqual(loaded['setup'],setup)
        self.assertEqual(saved['revision'],loaded['revision'])
        self.assertEqual(self.client.post('/builder-setup/api/export',json={'setup':setup}).get_json(),setup)
        self.assertEqual(self.client.post('/builder-setup/api/import',json={'setup':setup}).get_json()['setup'],setup)
        self.client.post('/builder-setup/api/save',json={'setup':setup,'name':'mapping','mode':'duplicate'})
        self.assertEqual(Path(self.temporary.name,'mapping.json').read_bytes(),original)
        setup['setup_name']='Changed';self.client.post('/builder-setup/api/save',json={'setup':setup,'name':'mapping','mode':'overwrite','expected_revision':saved['revision']})
        self.assertEqual(self.client.post('/builder-setup/api/save',json={'setup':setup,'name':'mapping','mode':'overwrite','expected_revision':saved['revision']}).status_code,409)

    def test_review_and_launch_checks_are_enforced_server_side(self):
        setup=setup_from_plan(plan_fixture());setup['mode']='single_operator_flow';scenario=generate_scenario(setup)['scenario']
        self.assertEqual(self.client.post('/launch',json=scenario).status_code,400)
        self.assertFalse(self.client.post('/builder-setup/api/review-status',json={'scenario':scenario}).get_json()['reviewed'])
        reviewed=self.client.post('/builder-setup/api/review',json={'scenario':scenario}).get_json()['scenario']
        self.assertEqual(self.client.post('/launch',json=reviewed).status_code,200)
        self.assertTrue(self.client.post('/builder-setup/api/review-status',json={'scenario':reviewed}).get_json()['reviewed'])
        reviewed['stations']['1']['name']='Renamed';self.assertEqual(self.client.post('/launch',json=reviewed).status_code,400)


if __name__=='__main__':unittest.main()
