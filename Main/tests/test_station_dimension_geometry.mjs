import assert from 'node:assert/strict';
import {resizeStationRect,nearestDimensionPoint,resolvedDimension,distanceFromSegment} from '../static/js/dimension-tools.js';
import {meterLabel} from '../static/js/smart-guides.js';
const s={x:100,y:200,w:150,h:96};
const cases=[
  ['se',{x:320,y:400},{x:100,y:200}],
  ['nw',{x:20,y:90},{x:250,y:296}],
  ['ne',{x:320,y:90},{x:100,y:296}],
  ['sw',{x:20,y:400},{x:250,y:200}],
];
for(const [corner,to,fixed] of cases) {
  const r=resizeStationRect(s,corner,to);
  const opposite=({se:[r.x,r.y],nw:[r.x+r.w,r.y+r.h],ne:[r.x,r.y+r.h],sw:[r.x+r.w,r.y]})[corner];
  assert.deepEqual(opposite,[fixed.x,fixed.y],corner);
  assert(r.w>=64&&r.h>=55);
}
assert.deepEqual(resizeStationRect(s,'se',{x:101,y:202}),{x:100,y:200,w:64,h:55});
const snap=nearestDimensionPoint({x:103,y:202},[{type:'station',id:'1',rect:s}],1.25);
assert.equal(snap.anchor.id,'1');assert.equal(snap.anchor.rx,0);assert.equal(snap.anchor.ry,0);
let station={...s};
const d={x:100,y:200,x2:250,y2:200,start_anchor:{type:'station',id:'1',rx:0,ry:0},end_anchor:{type:'station',id:'1',rx:1,ry:0}};
const resolve=()=>resolvedDimension(d,(_,id)=>id==='1'?station:null);
assert.equal(resolve().end.x,250);
station.w=300;station.x=300;
assert.deepEqual(resolve(),{start:{x:300,y:200},end:{x:600,y:200}});
assert.equal(meterLabel(300,50),'6.00 m');
assert.equal(meterLabel(300,100),'3.00 m');
assert.equal(distanceFromSegment({x:150,y:205},{x:100,y:200},{x:200,y:200}),5);
console.log('Geometry: fixed corners, minimum sizes, anchor updates, scale and segment hit-testing passed.');
