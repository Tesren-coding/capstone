// PQPR calculations use shared process timings and stable references.
export const categories = {
    in_line: {label: 'Green · In line'},
    out_of_line: {label: 'Orange · Out of line'},
    unique: {label: 'Blue · Low hit rate / unique'},
};

export function blankProject(version = 1) {
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
        manual_time: included.some(p => p.manual_time === null) ? null : included.reduce((sum,p) => sum + p.manual_time, 0),
        auto_time: included.some(p => p.auto_time === null) ? null : included.reduce((sum,p) => sum + p.auto_time, 0)};
}

export function displayTime(value) {
    return value === null ? 'Incomplete' : `${Number(value.toFixed(3))} min`;
}
