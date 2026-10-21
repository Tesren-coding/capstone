import assert from 'node:assert/strict';
import {sequenceToTasks,tasksToSequence,taskWorkSequenceIndex,defaultOperatorTask,clearMaterialBoxStandingSides} from '../static/js/operator-tasks.js';

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
assert.deepEqual(tasksToSequence([defaultOperatorTask('transfer')]),[{action:'pick',loc:''},{action:'drop',loc:''}]);
assert.deepEqual(tasksToSequence(sequenceToTasks([{action:'pick',loc:''}])),[{action:'pick',loc:''}]);
const mixedLocations = {Op6:{sequence:[
    {action:'pick',loc:'IN_1',standing_side:'left'},
    {action:'work',loc:'1',process:'p1',standing_side:'right'},
    {action:'drop',loc:'SWIP_1',standing_side:'top'},
    {action:'pick',loc:'SWIP_1',standing_side:'bottom'},
    {action:'drop',loc:'OUT_1',standing_side:'left'},
]}};
assert.equal(clearMaterialBoxStandingSides(mixedLocations, {
    IN_1:{type:'in'}, SWIP_1:{type:'swip'}, OUT_1:{type:'out'},
}),4);
assert.equal(clearMaterialBoxStandingSides(mixedLocations, {IN_1:{type:'in'}, SWIP_1:{type:'swip'}, OUT_1:{type:'out'}}),0);
assert.deepEqual(mixedLocations.Op6.sequence.filter(x => x.standing_side).map(x => x.loc),['1']);

const withWait = [
    {action:'pick',loc:'IN_1'}, {action:'drop',loc:'1'},
    {action:'wait',duration:7.5}, {action:'work',loc:'1',process:'p1'},
];
assert.deepEqual(sequenceToTasks(withWait).map(t=>t.kind),['transfer','wait','process']);
assert.deepEqual(tasksToSequence(sequenceToTasks(withWait)),withWait);
assert.deepEqual(tasksToSequence([defaultOperatorTask('wait')]), [{action:'wait',duration:1}]);

console.log('Operator task compilation, cross-operator handoffs, standing side and legacy roundtrip passed.');
