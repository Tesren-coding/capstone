"""C-shape geometry, break ownership and old-file defaults."""
from copy import deepcopy
import unittest
from line_layout import c_layout, break_count
from builder_setup import setup_from_plan, validate_setup, generate_scenario
from balancing_schema import validate_plan
from scenario_schema import ScenarioValidationError, review_planning_scenario
from simulation import run_scenario_simulation
from test_builder_setup import plan_fixture


class LineLayoutTests(unittest.TestCase):
    def test_each_break_orders_upper_leftward_and_lower_rightward(self):
        for length in range(2,10):
            ids=[str(i+1) for i in range(length)]
            for count in range(1,length):
                with self.subTest(length=length,count=count):
                    layout=c_layout(ids,ids[count-1]);pos=layout['positions']
                    self.assertEqual(layout['top_count'],count)
                    self.assertEqual(pos[ids[0]]['y'],layout['input']['y'])
                    self.assertGreater(layout['input']['x'],pos[ids[0]]['x'])
                    self.assertEqual(pos[ids[count-1]]['x'],pos[ids[count]]['x'])
                    self.assertGreater(pos[ids[count]]['y'],pos[ids[count-1]]['y'])
                    for i in range(count-1):self.assertGreater(pos[ids[i]]['x'],pos[ids[i+1]]['x'])
                    for i in range(count,length-1):self.assertLess(pos[ids[i]]['x'],pos[ids[i+1]]['x'])
                    self.assertEqual(layout['output']['y'],pos[ids[-1]]['y'])
                    self.assertGreater(layout['output']['x'],pos[ids[-1]]['x'])
                    self.assertTrue(all(p['x']>=0 for p in pos.values()))

    def test_default_invalid_and_single_station_breaks(self):
        self.assertEqual(break_count(['1','2','3','4','5']),3)
        self.assertEqual(break_count(['1','2','3'],'3'),2)
        self.assertEqual(break_count(['1','2','3'],'missing'),2)
        single=c_layout(['1'])
        self.assertGreater(single['input']['x'],single['positions']['1']['x'])
        self.assertGreater(single['output']['y'],single['input']['y'])
        self.assertEqual(single['input']['x'],single['output']['x'])
        self.assertEqual(c_layout([])['positions'],{})

    def test_plan_break_copies_to_setup_and_generation_without_mutating_source(self):
        plan=plan_fixture();plan['line_layout']={'shape':'c','break_after_step_id':'s1'}
        before=deepcopy(plan);setup=setup_from_plan(plan)
        self.assertEqual(setup['layout']['break_after_station_id'],'1')
        result=generate_scenario(setup);scenario=result['scenario']
        self.assertEqual(scenario['stations']['1']['y'],scenario['boxes']['IN_1']['y'])
        self.assertGreater(scenario['stations']['2']['y'],scenario['stations']['1']['y'])
        self.assertLess(scenario['stations']['2']['x'],scenario['stations']['3']['x'])
        self.assertEqual(scenario['planning_origin']['layout']['break_after_station_id'],'1')
        self.assertEqual(plan,before)

    def test_grouped_station_is_never_split_and_override_is_respected(self):
        plan=plan_fixture();plan['line_layout']={'shape':'c','break_after_step_id':'s2'}
        setup=setup_from_plan(plan);setup['mapping']['s2']='1'
        result=generate_scenario(setup)
        self.assertEqual(result['layout']['break_after_id'],'1')
        self.assertEqual(len(result['scenario']['stations']['1']['processes']),2)
        self.assertTrue(any('no longer an interior boundary' in n for n in result['notes']))
        setup['layout']['break_after_station_id']='1'
        self.assertEqual(generate_scenario(setup)['layout']['top_count'],1)

    def test_old_setup_defaults_to_c_and_work_only_always_has_endpoint_boxes(self):
        setup=setup_from_plan(plan_fixture(True));setup.pop('layout')
        self.assertEqual(validate_setup(setup),setup)
        scenario=generate_scenario(setup)['scenario']
        self.assertEqual(set(scenario['boxes']),{'IN_1','OUT_2'})
        self.assertEqual(scenario['planning_origin']['layout']['shape'],'c')
        self.assertTrue(all(s['action']=='work' for op in scenario['operators'].values() for s in op['sequence']))
        with self.assertRaises(ScenarioValidationError):review_planning_scenario(scenario)

    def test_break_does_not_change_ids_times_assignments_or_transport(self):
        setup=setup_from_plan(plan_fixture());setup['mode']='single_operator_flow'
        first=generate_scenario(setup)['scenario'];setup['layout']['break_after_station_id']='1'
        second=generate_scenario(setup)['scenario']
        self.assertEqual(first['operators']['Op1']['sequence'],second['operators']['Op1']['sequence'])
        for sid in first['stations']:self.assertEqual(first['stations'][sid]['processes'],second['stations'][sid]['processes'])
        events,_=run_scenario_simulation(review_planning_scenario(second))
        self.assertFalse(any(e['status']=='blocked' for e in events))
        self.assertTrue(any(e['status']=='dropoff' and e['loc']=='OUT_2' for e in events))

    def test_invalid_saved_layout_references_and_shapes_are_rejected(self):
        for shape,identifier in [('linear','s1'),('c','missing'),('c',[]),('c',1)]:
            plan=plan_fixture();plan['line_layout']={'shape':shape,'break_after_step_id':identifier}
            with self.subTest(shape=shape,id=identifier),self.assertRaises(ScenarioValidationError):validate_plan(plan)
        for identifier in ['99',[],1]:
            setup=setup_from_plan(plan_fixture());setup['layout']={'shape':'c','break_after_station_id':identifier}
            with self.subTest(id=identifier),self.assertRaises(ScenarioValidationError):validate_setup(setup)


if __name__=='__main__':unittest.main()
