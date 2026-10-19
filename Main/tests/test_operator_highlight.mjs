import assert from 'node:assert/strict';
import {visitedLocationsForOperator, operatorAtLegendPoint, operatorLegendEntries, sortOperatorIds} from '../static/js/operator-highlight.js';
const scenario = {
  stations: {'1':{},'2':{},'3':{}},
  boxes: {'box1':{type:'in'},'box2':{type:'swip'},'box3':{type:'out'},'arrow':{type:'direction'}},
  operators: {}
};
const op = {attached_to:{station_id:'1',side:'bottom'},sequence:[
  {action:'pick',loc:'box1'}, {action:'drop',loc:'box2'},
  {action:'work',loc:'2'}, {action:'drop',loc:'box3'},
  {action:'work',loc:'2'}, {action:'work',loc:'arrow'}, {action:'work',loc:'unknown'}
]};
assert.deepEqual([...visitedLocationsForOperator(op,scenario)].sort(), ['1','2','box1','box2','box3'].sort());
assert.deepEqual([...visitedLocationsForOperator({sequence:[]},scenario)],[]);
// Natural numeric sorting is essential once Op10+ exists, or save/load order
// differs from the order in which operators were originally created.
const unordered = ['Op10', 'Op3', 'Op2', 'Op11', 'Op1', 'Op21', 'Op9'];
assert.deepEqual(sortOperatorIds(unordered), ['Op1', 'Op2', 'Op3', 'Op9', 'Op10', 'Op11', 'Op21']);
assert.deepEqual(unordered, ['Op10', 'Op3', 'Op2', 'Op11', 'Op1', 'Op21', 'Op9'], 'must not mutate saved ordering');
assert.deepEqual(sortOperatorIds(['Op10', 'Operator B', 'Op2']).slice(0, 2), ['Op2', 'Op10']);
const list = operatorLegendEntries(['Op1','LongOperatorName'],1042);
assert.equal(operatorAtLegendPoint({x:list[0].x,y:list[0].y},['Op1','LongOperatorName'],1042),'Op1');
assert.equal(operatorAtLegendPoint({x:list[1].x,y:list[1].y},['Op1','LongOperatorName'],1042),'LongOperatorName');
assert.equal(operatorAtLegendPoint({x:list[0].x,y:100},['Op1','LongOperatorName'],1042),null);
assert.ok(list[1].left>=list[0].right);
console.log('Operator highlight model and canvas-legend hit test: passed.');
