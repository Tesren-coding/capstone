// Run without third-party dependencies: node tests/test_builder_snapping.mjs
import assert from 'node:assert/strict';
import {cLayout} from '../static/js/line-layout.js';
import {STATION_WIDTH, STATION_HEIGHT} from '../static/js/layout-geometry.js';
import {OPERATOR_RADIUS, OPERATOR_GAP, STATION_GAP,
  operatorPoint, operatorSlots, nearestOperatorSlot, snapStation,
  stationInsertPosition, updateAttachedOperators, detachStationOperators,
  remapOperatorAttachments} from '../static/js/builder-snapping.js';

assert.equal(STATION_WIDTH, 150);
assert.equal(STATION_HEIGHT, 96);
for (const count of [1,2,3,4,7]) {
  const ids = Array.from({length:count}, (_,i)=>String(i+1));
  for (const station of Object.values(cLayout(ids,ids[0]).positions)) {
    assert.equal(station.w, STATION_WIDTH);
    assert.equal(station.h, STATION_HEIGHT);
  }
}
const stations={'1':{x:200,y:300,w:150,h:96},'2':{x:520,y:300,w:150,h:96}};
const operators={};
const sides={top:{x:275,y:274},right:{x:376,y:348},bottom:{x:275,y:422},left:{x:174,y:348}};
for (const [side, expected] of Object.entries(sides)) {
  assert.deepEqual(operatorPoint(stations['1'],side),expected);
  assert.equal(Math.hypot(expected.x-operatorPoint(stations['1'],side).x,
      expected.y-operatorPoint(stations['1'],side).y),0);
}
assert.equal(sides.top.y + OPERATOR_RADIUS + OPERATOR_GAP,stations['1'].y);
assert.equal(operatorSlots(stations,operators).length,8);
assert.equal(nearestOperatorSlot(stations,operators,277,274,1).side,'top');
assert.equal(nearestOperatorSlot(stations,operators,277,274,2).side,'top');
assert.equal(nearestOperatorSlot(stations,operators,291,274,1).side,'top');
assert.equal(nearestOperatorSlot(stations,operators,291,274,2),null,
  'Screen-space snap tolerance must contract when zoomed in');
assert.equal(nearestOperatorSlot(stations,operators,310,274,0.5).side,'top');
operators.Op1={x:275,y:274,attached_to:{station_id:'1',side:'top'},sequence:[]};
assert.equal(operatorSlots(stations,operators).length,7);
assert.equal(nearestOperatorSlot(stations,operators,275,274,1),null,'occupied point excluded');
assert.equal(nearestOperatorSlot(stations,operators,275,274,1,'Op1').side,'top');
const snapped=snapStation(stations,'new',383,302,150,96,1);
assert.deepEqual({x:snapped.x,y:snapped.y},{x:200+150+STATION_GAP,y:300});
assert.equal(snapStation(stations,'new',383,302,150,96,4).x,383,
    'Zoomed-in tolerance is measured in screen pixels');
const inserted=stationInsertPosition({'1':stations['1']},275,348,150,96,1);
assert.equal(inserted.y,stations['1'].y+stations['1'].h+STATION_GAP);
assert.equal(inserted.x,stations['1'].x);
assert.equal(stationInsertPosition({},275,348,150,96).x,200);
stations['1'].x=240;stations['1'].y=330;
updateAttachedOperators(stations,operators,'1');
assert.deepEqual({x:operators.Op1.x,y:operators.Op1.y},operatorPoint(stations['1'],'top'));
remapOperatorAttachments(operators,{'1':'2','2':'1'});
assert.equal(operators.Op1.attached_to.station_id,'2');
assert.equal(operators.Op1.attached_to.side,'top');
remapOperatorAttachments(operators,{'2':'7'});
assert.equal(operators.Op1.attached_to.station_id,'7');
detachStationOperators(operators,'7');
assert.equal(operators.Op1.attached_to,undefined);
assert.deepEqual({x:operators.Op1.x,y:operators.Op1.y},{x:315,y:304},
  'Detach keeps final absolute coordinates');
console.log('Builder snapping and preview geometry: all checks passed.');
