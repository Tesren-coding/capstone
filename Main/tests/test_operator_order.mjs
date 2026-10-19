import assert from 'node:assert/strict';
import {orderedOperatorIds,remapOperatorOrder} from '../static/js/operator-order.js';

const actors = {
  Op10:{name:'Op10',color:[100,0,0],x:50,sequence:[{action:'work',loc:'3'}]},
  Op2:{name:'Op2',color:[0,100,0],x:20,sequence:[{action:'work',loc:'2'}]},
  Op1:{name:'Op1',color:[0,0,100],x:10,sequence:[{action:'work',loc:'1'}]},
};
assert.deepEqual(orderedOperatorIds(actors),['Op1','Op2','Op10']);
const result=remapOperatorOrder(actors,['Op10','Op1','Op2']);
assert.deepEqual(Object.keys(result.operators),['Op1','Op2','Op3']);
assert.equal(result.operators.Op1.x,50);
assert.equal(result.operators.Op2.x,10);
assert.equal(result.operators.Op3.x,20);
assert.deepEqual(result.operators.Op1.sequence,[{action:'work',loc:'3'}]);
assert.deepEqual(result.operators.Op1.color,[100,0,0]);
assert.equal(result.operators.Op1.name,'Op1');
assert.equal(result.changed,true);
assert.deepEqual(result.mapping,{Op10:'Op1',Op1:'Op2',Op2:'Op3'});
assert.deepEqual(actors.Op10,{name:'Op10',color:[100,0,0],x:50,sequence:[{action:'work',loc:'3'}]},'Source not mutated');
assert.throws(()=>remapOperatorOrder(actors,['Op1','Op1','Op2']));
assert.throws(()=>remapOperatorOrder(actors,['Op1','Op2']));
assert.equal(remapOperatorOrder({Op1:{name:'Op1',sequence:[]}},['Op1']).changed,false);
console.log('Operator reorder mappings and invariants: passed.');
