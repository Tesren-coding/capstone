"""Blank automatic time is zero; route membership and manual unknowns survive."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import app as web
from pqpr_schema import validate_pqpr, frame_totals
from pqpr_store import PQPRStore
from balancing_schema import validate_plan, plan_from_pqpr, analyse_plan
from builder_setup import setup_from_plan, generate_scenario
from scenario_schema import ScenarioValidationError
from test_pqpr import project
from test_pqpr_working_elements import broken_down_plan


class AutoTimeDefaultTests(unittest.TestCase):
    def test_legacy_null_auto_normalizes_without_mutating_source_or_manual(self):
        old=project();before=deepcopy(old);new=validate_pqpr(old)
        self.assertEqual(old,before)
        self.assertTrue(all(p['auto_time'] is not None for p in new['processes']))
        self.assertEqual(new['framesizes'][1]['timings']['p3'],{'manual_time':None,'auto_time':0})
        self.assertIsNone(frame_totals(new,new['framesizes'][1])['manual_time'])
        self.assertEqual(frame_totals(new,new['framesizes'][1])['auto_time'],0)
        self.assertEqual(set(new['framesizes'][0]['applicability']),{'p1','p2'})

    def test_current_missing_auto_defaults_zero_and_used_zero_cell_survives(self):
        data=validate_pqpr(project());data['framesizes'][0]['timings']['p1']={'manual_time':0}
        del data['processes'][0]['auto_time']
        normalized=validate_pqpr(data)
        self.assertEqual(normalized['processes'][0]['auto_time'],0)
        self.assertEqual(normalized['framesizes'][0]['timings']['p1'],{'manual_time':0,'auto_time':0})
        self.assertEqual(normalized['framesizes'][0]['applicability']['p1'],'required')
        plan=plan_from_pqpr(normalized,'f1')
        self.assertEqual(plan['processes'][0]['auto_time'],0)
        self.assertEqual(plan['steps'],[])

    def test_load_and_export_old_blank_auto_do_not_rewrite_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory,'old.json');path.write_text(json.dumps(project()));before=path.read_bytes()
            new=PQPRStore(directory).load('old.json')['project']
            self.assertEqual(path.read_bytes(),before)
            c=web.app.test_client();response=c.post('/pqpr/api/export',json={'project':new})
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.get_json()['framesizes'][1]['timings']['p3']['auto_time'],0)
            self.assertEqual(path.read_bytes(),before)

    def test_process_and_element_auto_null_and_missing_normalize_on_plan_import(self):
        data=broken_down_plan();data['processes'][0]['auto_time']=None
        data['steps'][0]['auto_time']=None;del data['steps'][1]['auto_time'];data['steps'][2]['manual_time']=None
        before=deepcopy(data);response=web.app.test_client().post('/line-balancing/api/import',json={'plan':data})
        self.assertEqual(response.status_code,200)
        plan=response.get_json()['plan'];self.assertEqual(data,before)
        self.assertEqual(plan['processes'][0]['auto_time'],0)
        self.assertTrue(all(s['auto_time']==0 for s in plan['steps']))
        self.assertIsNone(plan['steps'][2]['manual_time'])
        self.assertEqual(analyse_plan(plan)['unknown_auto'],[])
        self.assertIsNone(analyse_plan(plan)['manual_total'])

    def test_generation_accepts_blank_auto_and_still_rejects_blank_manual(self):
        plan=broken_down_plan();plan['steps'][1]['auto_time']=None
        scene=generate_scenario(setup_from_plan(plan))['scenario']
        self.assertEqual(scene['stations']['1']['processes'][1]['auto_time'],0)
        plan['steps'][1]['manual_time']=None
        with self.assertRaises(ScenarioValidationError):generate_scenario(setup_from_plan(plan))

    def test_bad_auto_values_are_rejected_instead_of_coerced_to_zero(self):
        for value in [-1,True,'',float('inf')]:
            data=project();data['processes'][0]['auto_time']=value
            with self.subTest(value=value),self.assertRaises(ScenarioValidationError):validate_pqpr(data)
            plan=broken_down_plan();plan['steps'][0]['auto_time']=value
            with self.subTest(value=value),self.assertRaises(ScenarioValidationError):validate_plan(plan)


if __name__=='__main__':unittest.main()
