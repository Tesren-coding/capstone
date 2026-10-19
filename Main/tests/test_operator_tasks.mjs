import assert from 'node:assert/strict';
import {sequenceToTasks,tasksToSequence,taskWorkSequenceIndex,defaultOperatorTask} from '../static/js/operator-tasks.js';

const fullCycle = [
    {action:'pick',loc:'IN_1'},
    {action:'drop',loc:'1'},
    {action:'work',loc:'1',process:'p1',standing_side:'right'},
    {action:'pick',loc:'1'},
    {action:'drop',loc:'SWIP_1'},
];
const tasks=sequenceToTasks(fullCycle);
assert.equal(tasks.length,1);
assert.equal(tasks[0].kind,'cycle');
assert.equal(taskWorkSequenceIndex(tasks,0),2);
assert.deepEqual(tasksToSequence(tasks),fullCycle);

const handoffs = [
    [{action:'pick',loc:'IN_1'},{action:'drop',loc:'1'}],
    [{action:'work',loc:'1',process:'p1'}],
    [{action:'pick',loc:'1'},{action:'drop',loc:'SWIP_1'}],
];
assert.deepEqual(handoffs.map(x=>sequenceToTasks(x)[0].kind),['transfer','process','transfer']);
for(const seq of handoffs) assert.deepEqual(tasksToSequence(sequenceToTasks(seq)),seq);
assert.equal(defaultOperatorTask('cycle').kind,'cycle');
assert.deepEqual(tasksToSequence([defaultOperatorTask('transfer')]),[{action:'pick',loc:'',wait_for_process:true},{action:'drop',loc:''}]);
assert.deepEqual(tasksToSequence(sequenceToTasks([{action:'pick',loc:''}])),[{action:'pick',loc:''}]);
console.log('Operator task compilation, cross-operator handoffs, standing side and legacy roundtrip passed.');
