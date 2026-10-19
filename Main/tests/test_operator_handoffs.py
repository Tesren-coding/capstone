"""Validation of cross-operator handoffs without Flask or SimPy."""
import unittest
from copy import deepcopy
from scenario_schema import validate_scenario, ScenarioValidationError

def scenario():
    station={'name':'Inspect','x':100,'y':100,'w':150,'h':96,'has_part':False,
             'processes':[{'id':'p1','name':'Inspection','manual_time':1.0,'auto_time':0.5}]}
    def op(x,sequence):return {'name':'Op1','x':x,'y':30,'color':[55,120,210],'sequence':sequence}
    return {'schema_version':2,'takt_time':10,
            'stations':{'1':station},
            'boxes':{'IN_1':{'type':'in','name':'Raw','x':10,'y':100,'w':60,'h':50,'start_count':15},
                     'OUT_1':{'type':'out','name':'Finished','x':350,'y':100,'w':60,'h':50,'capacity':150}},
            'operators':{'Op1':op(30,[{'action':'pick','loc':'IN_1','wait_for_process':True},{'action':'drop','loc':'1'}]),
                         'Op2':op(170,[{'action':'work','loc':'1','process':'p1'}]),
                         'Op3':op(310,[{'action':'pick','loc':'1','wait_for_process':True},{'action':'drop','loc':'OUT_1'}])}}

class HandoffContractTests(unittest.TestCase):
    def test_three_distinct_operators_share_station(self):
        data=scenario()
        self.assertEqual({k:v['sequence'] for k,v in validate_scenario(data)['operators'].items()},
                         {k:v['sequence'] for k,v in data['operators'].items()})
    def test_wait_for_process_must_be_bool_pick_only(self):
        data=scenario();data['operators']['Op3']['sequence'][0]['wait_for_process']='yes'
        with self.assertRaises(ScenarioValidationError):validate_scenario(data)
        data=scenario();data['operators']['Op2']['sequence'][0]['wait_for_process']=True
        with self.assertRaises(ScenarioValidationError):validate_scenario(data)
    def test_old_sequences_need_no_wait_field(self):
        data=scenario()
        for op in data['operators'].values():
            for step in op['sequence']:step.pop('wait_for_process',None)
        self.assertEqual({k:v['sequence'] for k,v in validate_scenario(data)['operators'].items()},
                         {k:v['sequence'] for k,v in data['operators'].items()})

if __name__=='__main__':unittest.main()
