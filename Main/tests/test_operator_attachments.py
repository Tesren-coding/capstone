"""Optional layout attachments must survive imports without changing old JSON."""
from copy import deepcopy
import unittest
from scenario_schema import validate_scenario, ScenarioValidationError


def sample():
    return {'schema_version':2,'takt_time':30,
        'stations': {'1':{'x':201,'y':245,'w':150,'h':96,'name':'S1','has_part':False,'cycle_time':2,
            'processes':[{'id':'p1','name':'Weld','manual_time':2,'auto_time':0}]}},
        'operators':{'Op1':{'x':276,'y':219,'color':[30,110,210],'name':'Op1',
            'sequence':[]}},'boxes':{}}


class AttachmentContractTests(unittest.TestCase):
    def test_optional_attachment_round_trip(self):
        original=sample()
        original['operators']['Op1']['attached_to']={'station_id':'1','side':'top'}
        snapshot=deepcopy(original)
        data=validate_scenario(original,require_runnable=False)
        self.assertEqual(data,original)
        self.assertEqual(original,snapshot)
        self.assertEqual(validate_scenario(data,require_runnable=False),data)

    def test_legacy_free_operator_position_and_station_size_preserved(self):
        original=sample()
        original['stations']['1']['w']=230
        original['stations']['1']['h']=140
        original['operators']['Op1']['x']=388.75
        data=validate_scenario(original,require_runnable=False)
        self.assertNotIn('attached_to',data['operators']['Op1'])
        self.assertEqual(data['stations']['1']['w'],230)
        self.assertEqual(data['stations']['1']['h'],140)
        self.assertEqual(data['operators']['Op1']['x'],388.75)

    def test_invalid_refs_and_duplicate_sides_rejected(self):
        for attachment in [None,{},'1',{'station_id':'99','side':'top'},
            {'station_id':1,'side':'top'},{'station_id':'1','side':'middle'},
            {'station_id':'1','side':'left','unknown':1}]:
            original=sample()
            original['operators']['Op1']['attached_to']=attachment
            with self.subTest(attachment=attachment),self.assertRaises(ScenarioValidationError):
                validate_scenario(original,require_runnable=False)
        original=sample()
        original['operators']['Op1']['attached_to']={'station_id':'1','side':'bottom'}
        original['operators']['Op2']={**original['operators']['Op1'],'name':'Op2'}
        with self.assertRaises(ScenarioValidationError):
            validate_scenario(original,require_runnable=False)


if __name__=='__main__':unittest.main()
