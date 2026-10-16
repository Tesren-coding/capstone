import assert from 'node:assert/strict';
import {smartSnapRect,nearestGapMeasurements,meterLabel,metersFromCanvas} from '../static/js/smart-guides.js';

const reference=[{id:'1',type:'station',rect:{x:300,y:200,w:150,h:96}}];
const between=(x,y,w=150,h=96,zoom=1,options={})=>smartSnapRect({x,y,w,h},reference,zoom,options);
assert.equal(meterLabel(150,50),'3.00 m');
assert.equal(meterLabel(22,50),'0.44 m');
assert.equal(meterLabel(23,100),'0.23 m');
assert.equal(metersFromCanvas(-50,25),2);
assert.equal(meterLabel(25,0),'0.50 m', 'invalid scale falls back to 50 px/m');

// Left-edge and vertical-center alignment have different anchors, both possible.
let result=between(307,211);
assert.equal(result.x,300);
assert.ok(result.guides.some(g=>g.axis==='x'&&g.at===300));
result=between(460,200);
assert.equal(result.y,200);
assert.ok(result.guides.some(g=>g.axis==='y'));
result=between(305,211,140,80); // nearest anchor is center when widths differ
assert.equal(result.x,305);
assert.ok(result.guides.some(g=>g.kind==='center'));

// Center-to-center snap without near edges; the reference center is at x=375.
result=between(309,211,130,80);
assert.equal(result.x,310); // moving center 374 -> 375, edge 309 -> 300 is beyond 10 px
assert.ok(result.guides.some(g=>g.kind==='center' && g.axis==='x'));

// Dock to station with 22 px clearance; measurement converts to 0.44m.
result=between(476,200,150,96,1,{dockStations:true});
assert.equal(result.x,472);
assert.equal(meterLabel(result.measurements.find(m=>m.axis==='x').distance,50),'0.44 m');

// Zoom affects snapping tolerance in screen px rather than world px.
assert.equal(between(307,211,150,96,2).x,307);
assert.equal(between(307,211,150,96,1).x,300);

// Different rectangular item types may be used as references.
const box=[{id:'IN_1',type:'box',rect:{x:650,y:200,w:90,h:60}}];
result=smartSnapRect({x:747,y:201,w:90,h:60},box,1);
assert.equal(result.x,740); // left-to-right alignment
assert.equal(result.y,200);

// Do not attract items far apart on the perpendicular axis.
result=between(305,850);
assert.equal(result.x,305);assert.equal(result.y,850);
assert.equal(result.guides.length,0);

// Gap is defined by nearest edges; when rectangles overlap there is no gap.
let metrics=nearestGapMeasurements({x:600,y:230,w:150,h:96},reference);
assert.equal(metrics.find(m=>m.axis==='x')?.distance,150);
metrics=nearestGapMeasurements({x:420,y:220,w:150,h:96},reference);
assert.equal(metrics.length,0);

// Holding Alt is implemented by passing snap:false; measurements remain visible.
result=between(305,200,150,96,1,{snap:false});
assert.equal(result.x,305);assert.equal(result.guides.length,0);

// Direction/selection bounds may be wide and rotated; no scaling assumptions.
result=smartSnapRect({x:290,y:199,w:875,h:85}, reference, 1);
assert.equal(result.y,200);
console.log('Smart snapping: edges/centers/gaps, px/m, 2 decimals, zoom, references, opt-out passed.');
