// Matrix cells own timings; catalog values are optional defaults for new cells.
export const categories = {
    in_line: {label: 'Green · In line'},
    out_of_line: {label: 'Orange · Out of line'},
    unique: {label: 'Blue · Low hit rate / unique'},
};

export function blankProject(version = 2) {
    return {document_type: 'pqpr', schema_version: version, project_name: 'New PQPR project',
        processes: [], framesizes: [], next_process_id: 1, next_framesize_id: 1};
}

export function nextId(project, kind) {
    const prefix = kind === 'processes' ? 'p' : 'f';
    const counter = kind === 'processes' ? 'next_process_id' : 'next_framesize_id';
    const largest = project[kind].reduce((max, item) => Math.max(max, Number(item.id.slice(1)) || 0), 0);
    const value = Math.max(largest + 1, Number(project[counter]) || 1);
    project[counter] = value + 1;
    return prefix + value;
}

export function frameTotals(project, frame) {
    const included = project.processes.filter(process => Object.hasOwn(frame.applicability, process.id));
    return {process_count: included.length,
        optional_count: included.filter(p => frame.applicability[p.id] === 'optional').length,
        manual_time: included.some(p => cellTiming(frame,p).manual_time === null) ? null : included.reduce((sum,p) => sum + cellTiming(frame,p).manual_time, 0),
        auto_time: included.reduce((sum,p) => sum + (cellTiming(frame,p).auto_time ?? 0), 0)};
}

export function cellTiming(frame, process) {
    return frame.timings?.[process.id] ?? {manual_time:null, auto_time:null};
}
export function setCellTime(frame, process, field, value) {
    frame.timings ??= {};
    const used = Object.hasOwn(frame.applicability, process.id);
    if (!used && value === null) return;
    if (!used) {
        frame.applicability[process.id] = 'required';
        frame.timings[process.id] = {manual_time:process.manual_time, auto_time:process.auto_time ?? 0};
    }
    if (!frame.timings[process.id]) return;
    frame.timings[process.id][field] = field === 'auto_time' && value === null ? 0 : value;
    const time = frame.timings[process.id];
    time.auto_time ??= 0;
}
export function clearCell(frame, processId) {
    delete frame.applicability[processId];
    delete frame.timings[processId];
}

export function displayTime(value) {
    return value === null ? 'Incomplete' : `${Number(value.toFixed(3))} min`;
}
