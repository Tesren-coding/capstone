// Run: node tests/test_line_direction.mjs
import assert from 'node:assert/strict';
import {
  directionAngle, directionContainsPoint, directionCenter,
  directionLocalPoint, directionResizeHandle, resizeDirectionFromPoint
} from '../static/js/line-direction.js';

const marker = {x:250, y:160, w:220, h:28, rotation:0, flip_horizontal:false, flip_vertical:false};
assert.deepEqual(directionCenter(marker), {x:360,y:174});
assert.equal(directionAngle(marker), 0);
assert.equal(directionContainsPoint(marker, 360, 174), true);
assert.equal(directionContainsPoint(marker, 360, 220), false);
assert.deepEqual(directionResizeHandle(marker), {x:470,y:188});
resizeDirectionFromPoint(marker, 500, 206);
assert.equal(marker.w, 280);
assert.equal(marker.h, 64);
assert.deepEqual(directionCenter(marker), {x:360,y:174});
marker.rotation = 90;
assert.ok(Math.abs(directionAngle(marker) - Math.PI/2) < 1e-9);
assert.equal(directionContainsPoint(marker,360,310),true);
assert.equal(directionContainsPoint(marker,495,174),false);
const handle = directionResizeHandle(marker);
const local = directionLocalPoint(marker,handle.x,handle.y);
assert.ok(Math.abs(local.x - marker.w/2) < 1e-9);
assert.ok(Math.abs(local.y - marker.h/2) < 1e-9);
marker.flip_horizontal = true;
marker.flip_vertical = true;
assert.equal(directionContainsPoint(marker, 360, 310), true, 'flipping should not change hit-testing');
console.log('Direction transforms and zoom-independent geometry passed.');
