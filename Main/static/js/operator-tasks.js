// Task-oriented authoring layer. The low-level sequence remains authoritative
// for SimPy, playback, legacy saves and standard-work exporters.
// A task can be given to any operator; station inventory provides the handoff.
const copy = value => JSON.parse(JSON.stringify(value));

export function sequenceToTasks(sequence = []) {
    const tasks = [];
    let i = 0;
    while (i < sequence.length) {
        const a = sequence[i], b = sequence[i+1], c = sequence[i+2], d = sequence[i+3], e = sequence[i+4];
        if (a?.action === 'pick' && b?.action === 'drop' && c?.action === 'work' &&
            d?.action === 'pick' && e?.action === 'drop' &&
            b.loc === c.loc && c.loc === d.loc) {
            tasks.push({kind:'cycle',source:a.loc,source_side:a.standing_side,
                station:c.loc,process:c.process,work_side:c.standing_side,
                drop_side:b.standing_side,pick_side:d.standing_side,wait_for_process:d.wait_for_process,
                target:e.loc,target_side:e.standing_side});
            i += 5;
        } else if (a?.action === 'pick' && b?.action === 'drop') {
            tasks.push({kind:'transfer',source:a.loc,source_side:a.standing_side,
                target:b.loc,target_side:b.standing_side,wait_for_process:a.wait_for_process});
            i += 2;
        } else if (a?.action === 'wait') {
            tasks.push({kind:'wait', duration:a.duration});
            i += 1;
        } else if (a?.action === 'work') {
            tasks.push({kind:'process',station:a.loc,process:a.process,work_side:a.standing_side});
            i += 1;
        } else {
            // Incomplete/nonstandard sequences stay editable in the advanced editor.
            tasks.push({kind:'legacy',step:copy(a)});
            i += 1;
        }
    }
    return tasks;
}

function action(name, loc, options = {}) {
    const result = {action:name,loc:loc ?? ''};
    if (name === 'work') result.process = options.process ?? '';
    if (options.side) result.standing_side = options.side;
    // Preserve legacy flags when converting older saved tasks; simulation no
    // longer uses them as station-wide completion prerequisites.
    if (options.wait_for_process !== undefined && name === 'pick') result.wait_for_process = options.wait_for_process;
    return result;
}

export function tasksToSequence(tasks = []) {
    return tasks.flatMap(task => {
        switch (task.kind) {
            case 'transfer':
                return [action('pick',task.source,{side:task.source_side,wait_for_process:task.wait_for_process}),
                    action('drop',task.target,{side:task.target_side})];
            case 'process':
                return [action('work',task.station,{process:task.process,side:task.work_side})];
            case 'cycle':
                return [action('pick',task.source,{side:task.source_side,wait_for_process:task.wait_for_process}),
                    action('drop',task.station,{side:task.drop_side}),
                    action('work',task.station,{process:task.process,side:task.work_side}),
                    action('pick',task.station,{side:task.pick_side,wait_for_process:task.wait_for_process}),
                    action('drop',task.target,{side:task.target_side})];
            case 'wait':
                return [{action:'wait', duration:task.duration}];
            case 'legacy':
                return task.step ? [copy(task.step)] : [];
            default: return [];
        }
    });
}

export function taskWorkSequenceIndex(tasks, taskIndex) {
    const before = tasksToSequence(tasks.slice(0, taskIndex)).length;
    if (tasks[taskIndex]?.kind === 'process') return before;
    if (tasks[taskIndex]?.kind === 'cycle') return before+2;
    return -1;
}

export function defaultOperatorTask(kind) {
    switch (kind) {
        case 'transfer': return {kind, source:'', target:''};
        case 'process': return {kind,station:'',process:''};
        case 'cycle': return {kind,source:'',station:'',process:'',target:''};
        case 'wait': return {kind, duration:1};
        default: throw new Error('Unknown task type.');
    }
}


// A standing side only applies to stations. Older saved tasks can retain a
// side after their source/destination changes to an IN/OUT/SWIP box. Remove
// those unused hints while keeping the operator's actions and station sides.
export function clearMaterialBoxStandingSides(operators = {}, boxes = {}) {
    let count = 0;
    for (const operator of Object.values(operators || {})) {
        for (const step of Array.isArray(operator?.sequence) ? operator.sequence : []) {
            const box = boxes?.[step?.loc];
            if (box && ['in', 'out', 'swip'].includes(box.type) &&
                    Object.hasOwn(step, 'standing_side')) {
                delete step.standing_side;
                count++;
            }
        }
    }
    return count;
}
