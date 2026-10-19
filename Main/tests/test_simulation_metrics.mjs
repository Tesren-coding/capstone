import assert from 'node:assert/strict';
import {startingSwipMetrics, liveLineMetrics} from '../static/js/simulation-metrics.js';

const scenario = {
  stations: {'1':{has_part:true},'2':{has_part:false},'3':{has_part:true}},
  boxes: {
    'in':{type:'in', start_count:20, has_part:true},
    'swip1':{type:'swip', has_part:true},
    'swip2':{type:'swip', has_part:false},
    'swip3':{type:'swip', has_part:true},
    'out':{type:'out', has_part:true},
    'direction':{type:'direction',has_part:true},
  },
};
assert.deepEqual(startingSwipMetrics(scenario), {
    totalSwip:24, swipBoxes:3, swipBoxesWithParts:2, stationParts:2,
    inBoxParts:20, inBoxes:1,
    categories: [
      {key:'stations', label:'Stations with parts', value:2, color:'#2b65ad'},
      {key:'swipBoxes', label:'SWIP boxes with parts', value:2, color:'#e28b18'},
      {key:'inBoxes', label:'IN boxes starting parts', value:20, color:'#2f9d57'},
    ],
});
assert.equal(startingSwipMetrics({}).totalSwip, 0);
assert.equal(startingSwipMetrics({boxes: {raw: {type:'in', start_count:4}}}).totalSwip, 4);
const state = {
  stationState: {'1':{hasPart:false},'2':{hasPart:true},'3':{hasPart:true}},
  boxState: {
    'in':{type:'in',remaining:14},'swip1':{type:'swip',has_part:false},
    'swip2':{type:'swip',has_part:true},'swip3':{type:'swip',has_part:true},
    'out':{type:'out',count:6},'out2':{type:'out',count:1},'direction':{type:'direction',count:100},
  },
  carrying:{Op1:true,Op2:false,Op3:true},
};
assert.deepEqual(liveLineMetrics(state), {
  currentWip:6, stationParts:2, swipBoxParts:2, partsCarried:2,
  finishedGoods:7, rawRemaining:14,
});
assert.equal(liveLineMetrics(null).currentWip, 0);
console.log('SWIP metrics: station, buffer and IN starting parts; live WIP calculations passed.');
