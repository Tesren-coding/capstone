import assert from 'node:assert/strict';
import {visitedLocationsForOperator, operatorAtLegendPoint, operatorLegendEntries} from '../static/js/operator-highlight.js';
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
const list = operatorLegendEntries(['Op1','LongOperatorName'],1042);
assert.equal(operatorAtLegendPoint({x:list[0].x,y:list[0].y},['Op1','LongOperatorName'],1042),'Op1');
assert.equal(operatorAtLegendPoint({x:list[1].x,y:list[1].y},['Op1','LongOperatorName'],1042),'LongOperatorName');
assert.equal(operatorAtLegendPoint({x:list[0].x,y:100},['Op1','LongOperatorName'],1042),null);
assert.ok(list[1].left>=list[0].right);
console.log('Operator highlight model and canvas-legend hit test: passed.');
