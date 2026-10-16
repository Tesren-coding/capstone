import {escapeHtml as esc} from './canvas-tools.js';
import {installDrag,dragHandle,moveBefore,rowDrop,beforeFromDrop} from './drag-sort.js';
import {postJson, requestJson} from './api.js';
import {blankProject, nextId, frameTotals, displayTime, categories} from './pqpr-model.js';

const app = document.getElementById('pqpr-app');
const version = Number(app.dataset.schemaVersion);
const status = document.getElementById('pqpr-status');
const workspace = document.getElementById('pqpr-workspace');
const projectName = document.getElementById('pqpr-project-name');
const matrix = document.getElementById('pqpr-matrix');
const processRows = document.getElementById('pqpr-processes');
const frameRows = document.getElementById('pqpr-frames');
const fileInput = document.getElementById('pqpr-file');
const select = document.getElementById('pqpr-project-select');
const draftKey = 'capstone-pqpr-draft';
let project = blankProject(version);
let loadedFilename = null, loadedRevision = null, savedSnapshot = JSON.stringify(project), busy = false;

function say(message, error = false) {
    status.textContent = message;
    status.classList.toggle('pqpr-status--error', error);
}
function setBusy(value) {
    busy = value;
    workspace.disabled = value;
    app.querySelectorAll('[data-file-action]').forEach(control => { control.disabled = value; });
}
function remember() {
    try { sessionStorage.setItem(draftKey, JSON.stringify({project, loadedFilename, loadedRevision, savedSnapshot})); }
    catch { say('Draft could not be kept in this browser. Save or export your project.', true); }
}
function changed() { return JSON.stringify(project) !== savedSnapshot; }
function updateSummary() {
    document.getElementById('pqpr-frame-count').textContent = project.framesizes.length;
    document.getElementById('pqpr-process-count').textContent = project.processes.length;
    document.getElementById('pqpr-timing-count').textContent = project.processes.filter(p => p.manual_time === null || p.auto_time === null).length;
    document.getElementById('pqpr-frame-summary').textContent = `${project.framesizes.length} products`;
    document.getElementById('pqpr-process-summary').textContent = `${project.processes.length} processes`;
    document.getElementById('pqpr-draft-state').textContent = changed() ? 'Unsaved changes' : loadedFilename ? `Saved · ${loadedFilename}` : 'New / imported project';
    project.framesizes.forEach(frame => {
        const node = matrix.querySelector(`[data-totals="${frame.id}"]`);
        if (!node) return;
        const totals = frameTotals(project, frame);
        node.innerHTML = `<strong>${totals.process_count} processes</strong><small>${totals.optional_count} sometimes</small><small>Manual: ${displayTime(totals.manual_time)}</small><small>Auto: ${displayTime(totals.auto_time)}</small>`;
    });
}
function touch() { updateSummary(); remember(); }

function renderMatrix() {
    if (!project.processes.length || !project.framesizes.length) {
        matrix.innerHTML = '<div class="pqpr-empty"><strong>Build your process matrix</strong><p>Add a framesize and a process, or import your PQPR workbook to start.</p></div>';
        updateSummary(); return;
    }
    matrix.innerHTML = `<table class="pqpr-matrix"><thead><tr><th class="pqpr-sticky-frame" scope="col">Framesize / product</th><th class="pqpr-sticky-total" scope="col">Route summary</th>${project.processes.map((p,index) => `<th class="cat-${p.category}" scope="col"><span class="pqpr-column-number">${index+1}</span><span>${esc(p.name)}</span><small>M ${p.manual_time === null ? '—' : p.manual_time} · A ${p.auto_time === null ? '—' : p.auto_time} min</small></th>`).join('')}</tr></thead><tbody>${project.framesizes.map(frame => `<tr><th class="pqpr-sticky-frame" scope="row"><strong>${esc(frame.name)}</strong><small>${esc([frame.stage && 'Stage '+frame.stage, frame.component].filter(Boolean).join(' · '))}</small></th><td class="pqpr-sticky-total" data-totals="${frame.id}"></td>${project.processes.map(p => {
        const included = Object.hasOwn(frame.applicability, p.id), optional = frame.applicability[p.id] === 'optional';
        return `<td class="pqpr-applicability ${included ? 'cat-'+p.category : ''}" data-cell-frame="${frame.id}" data-cell-process="${p.id}"><label><input type="checkbox" data-include data-frame="${frame.id}" data-process="${p.id}" ${included ? 'checked' : ''} aria-label="${esc(frame.name+' — '+p.name)}"><span>${included ? 'Included' : 'Not used'}</span></label><select data-frequency data-frame="${frame.id}" data-process="${p.id}" ${included ? '' : 'hidden'} aria-label="${esc(frame.name+' — '+p.name+' frequency')}"><option value="required" ${optional ? '' : 'selected'}>Always (P)</option><option value="optional" ${optional ? 'selected' : ''}>Sometimes (X)</option></select></td>`;
    }).join('')}</tr>`).join('')}</tbody></table>`;
    updateSummary();
}

function renderEditors() {
    frameRows.innerHTML = project.framesizes.map((f,i) => `<tr data-frame-row="${f.id}"><td><input data-frame="${f.id}" data-field="name" value="${esc(f.name)}" aria-label="Framesize ${i+1} name"></td><td><input data-frame="${f.id}" data-field="stage" value="${esc(f.stage)}" aria-label="Framesize ${i+1} stage"></td><td><input data-frame="${f.id}" data-field="component" value="${esc(f.component)}" aria-label="Framesize ${i+1} component"></td><td class="pqpr-row-actions">${dragHandle('pqpr-framesizes',f.id,f.name)}<button data-frame-action="remove" data-id="${f.id}">Remove</button></td></tr>`).join('');
    processRows.innerHTML = project.processes.map((p,i) => `<tr data-process-row="${p.id}" class="cat-${p.category}"><td class="pqpr-process-number">${i+1}</td><td><input data-process="${p.id}" data-field="name" value="${esc(p.name)}" aria-label="Process ${i+1} name"></td><td><select data-process="${p.id}" data-field="category" aria-label="Process ${i+1} color">${Object.entries(categories).map(([key,option]) => `<option value="${key}" ${p.category===key?'selected':''}>${option.label}</option>`).join('')}</select></td><td><input data-process="${p.id}" data-field="manual_time" type="number" min="0" step="any" value="${p.manual_time ?? ''}" placeholder="Unknown" aria-label="Process ${i+1} manual minutes"></td><td><input data-process="${p.id}" data-field="auto_time" type="number" min="0" step="any" value="${p.auto_time ?? ''}" placeholder="Unknown" aria-label="Process ${i+1} auto minutes"></td><td class="pqpr-row-actions">${dragHandle('pqpr-processes',p.id,p.name)}<button data-process-action="remove" data-id="${p.id}">Remove</button></td></tr>`).join('');
}
function render() { projectName.value = project.project_name; renderEditors(); renderMatrix(); }
function applyProject(data) {
    project = structuredClone(data); render();
}
function confirmReplace() { return !changed() || confirm('Replace your unsaved PQPR changes?'); }
async function refreshFiles() {
    const data = await requestJson('/pqpr/api/projects');
    select.replaceChildren(new Option('Select saved project', ''));
    data.files.forEach(filename => select.add(new Option(filename.replace(/\.json$/, ''), filename)));
    if (loadedFilename) select.value = loadedFilename;
}

projectName.addEventListener('input', () => { project.project_name = projectName.value; touch(); });
processRows.addEventListener('input', event => {
    const input = event.target;
    if (!input.dataset.field || !input.dataset.process) return;
    const process = project.processes.find(p => p.id === input.dataset.process);
    process[input.dataset.field] = input.dataset.field.endsWith('_time') ? (input.value === '' ? null : Number(input.value)) : input.value;
    input.closest('tr').className = 'cat-' + process.category;
    renderMatrix(); touch();
});
frameRows.addEventListener('input', event => {
    const input = event.target;
    if (!input.dataset.field || !input.dataset.frame) return;
    project.framesizes.find(f => f.id === input.dataset.frame)[input.dataset.field] = input.value;
    renderMatrix(); touch();
});
matrix.addEventListener('change', event => {
    const input = event.target, fid = input.dataset.frame, pid = input.dataset.process;
    if (!fid || !pid) return;
    const frame = project.framesizes.find(f => f.id === fid);
    const process = project.processes.find(p => p.id === pid);
    if (input.hasAttribute('data-include')) {
        if (input.checked) frame.applicability[pid] = 'required'; else delete frame.applicability[pid];
        const cell = input.closest('td'), frequency = cell.querySelector('select');
        cell.className = 'pqpr-applicability' + (input.checked ? ' cat-'+process.category : '');
        cell.querySelector('label span').textContent = input.checked ? 'Included' : 'Not used';
        frequency.hidden = !input.checked; frequency.value = 'required';
    } else if (input.hasAttribute('data-frequency')) { frame.applicability[pid] = input.value; }
    touch();
});
function rowAction(kind, id, action) {
    const list = project[kind], index = list.findIndex(item => item.id === id);
    if (action === 'remove') {
        const references = kind === 'processes' ? project.framesizes.filter(f => Object.hasOwn(f.applicability,id)).length : 0;
        if (!confirm(`Remove "${list[index].name}"?${references ? ' Its checks in '+references+' framesize(s) will also be removed.' : ''}`)) return;
        list.splice(index,1);
        if (kind === 'processes') project.framesizes.forEach(f => delete f.applicability[id]);
    }
    renderEditors(); renderMatrix(); touch();
}
installDrag(app,{
    source(node){if(busy)return null;const kind=node.dataset.dragType.replace('pqpr-','');if(!['processes','framesizes'].includes(kind))return null;return {kind,id:node.dataset.dragId,label:project[kind].find(i=>i.id===node.dataset.dragId).name};},
    target(hit,event,data){const row=hit.closest(data.kind==='processes'?'[data-process-row]':'[data-frame-row]');if(!row)return null;return {...rowDrop(row,event.clientY),id:row.dataset.processRow||row.dataset.frameRow};},
    drop(data,where){moveBefore(project[data.kind],data.id,beforeFromDrop(project[data.kind],where.id,where.after));renderEditors();renderMatrix();touch();say('Order updated; applicability retained.');},
    keyboard(data,key){const list=project[data.kind],index=list.findIndex(i=>i.id===data.id),other=index+(['ArrowUp','ArrowLeft'].includes(key)?-1:1);if(other<0||other>=list.length)return;[list[index],list[other]]=[list[other],list[index]];renderEditors();renderMatrix();touch();app.querySelector(`[data-drag-id="${data.id}"]`)?.focus();}
});
processRows.addEventListener('click', event => { const b=event.target.closest('[data-process-action]'); if(b) rowAction('processes',b.dataset.id,b.dataset.processAction); });
frameRows.addEventListener('click', event => { const b=event.target.closest('[data-frame-action]'); if(b) rowAction('framesizes',b.dataset.id,b.dataset.frameAction); });
document.getElementById('pqpr-add-process').addEventListener('click', () => {
    const id=nextId(project,'processes');
    project.processes.push({id,name:'New process',category:'in_line',manual_time:null,auto_time:null});
    renderEditors(); renderMatrix(); touch();
    const panel=document.getElementById('pqpr-processes-panel'); panel.open=true;
    const input=processRows.querySelector(`[data-process="${id}"][data-field="name"]`); input.focus(); input.select();
});
document.getElementById('pqpr-add-frame').addEventListener('click', () => {
    const id=nextId(project,'framesizes');
    project.framesizes.push({id,name:'New framesize',stage:'',component:'',applicability:{}});
    renderEditors(); renderMatrix(); touch();
    document.getElementById('pqpr-frames-panel').open=true;
    const input=frameRows.querySelector(`[data-frame="${id}"][data-field="name"]`); input.focus(); input.select();
});
document.getElementById('pqpr-new').addEventListener('click', () => {
    if(busy || !confirmReplace()) return;
    project=blankProject(version); loadedFilename=loadedRevision=null; savedSnapshot=JSON.stringify(project);
    render(); remember(); select.value=''; say('New project. Name the line, then add its framesizes and processes.');
});

function chooseSaveMode(filename) {
    return new Promise(resolve => {
        const dialog=document.getElementById('pqpr-save-dialog');
        document.getElementById('pqpr-save-message').textContent=`Save changes to "${filename}" or create a numbered copy?`;
        const finish=mode=>{dialog.close();resolve(mode);};
        dialog.querySelectorAll('[data-save-mode]').forEach(b=>b.onclick=()=>finish(b.dataset.saveMode==='cancel'?null:b.dataset.saveMode));
        dialog.oncancel=e=>{e.preventDefault();finish(null);};dialog.showModal();
    });
}
document.getElementById('pqpr-save').addEventListener('click', async () => {
    setBusy(true);
    try {
        const snapshot=structuredClone(project);
        let filename=loadedFilename, mode=filename?await chooseSaveMode(filename):'create';
        if(!mode)return;
        async function submit(){
            const response=await fetch('/pqpr/api/save',{method:'POST',headers:{'Content-Type':'application/json'},
                body:JSON.stringify({project:snapshot,name:snapshot.project_name,filename,mode,expected_revision:filename===loadedFilename?loadedRevision:null})});
            return response.json();
        }
        let result=await submit();
        if(result.status==='exists') {filename=result.filename;mode=await chooseSaveMode(filename);if(!mode)return;result=await submit();}
        if(result.status!=='saved')throw new Error(result.errors?.join('\n')||result.error||'Could not save project.');
        loadedFilename=result.filename;loadedRevision=result.revision;savedSnapshot=JSON.stringify(snapshot);
        touch();await refreshFiles();say(`Saved "${loadedFilename}".`);
    }catch(error){say(error.message,true);}finally{setBusy(false);}
});
document.getElementById('pqpr-load').addEventListener('click', async () => {
    if(!select.value){say('Choose a saved PQPR project.');return;}
    const filename=select.value;setBusy(true);
    try {
        const data=await requestJson('/pqpr/api/projects/'+encodeURIComponent(filename));
        if(!data.found)throw new Error('This project no longer exists.');
        if(!confirmReplace())return;
        loadedFilename=data.filename;loadedRevision=data.revision;savedSnapshot=JSON.stringify(data.project);
        applyProject(data.project);remember();say(`Loaded "${filename}".`);
    }catch(error){say(error.message,true);}finally{setBusy(false);}
});
document.getElementById('pqpr-import').addEventListener('click',()=>fileInput.click());
function chooseWorksheet(choices) {
    return new Promise(resolve=>{
        const dialog=document.getElementById('pqpr-sheet-dialog'), choice=document.getElementById('pqpr-sheet-select');
        choice.replaceChildren(...choices.map(item=>new Option(`${item.name} · ${item.process_count} processes`,item.name)));
        const finish=name=>{dialog.close();resolve(name);};
        document.getElementById('pqpr-sheet-import').onclick=()=>finish(choice.value);
        document.getElementById('pqpr-sheet-cancel').onclick=()=>finish(null);
        dialog.oncancel=e=>{e.preventDefault();finish(null);};dialog.showModal();
    });
}
fileInput.addEventListener('change',async()=>{
    const file=fileInput.files[0];if(!file)return;setBusy(true);
    try {
        let result;
        if(file.name.toLowerCase().endsWith('.xlsx')) {
            async function readSheet(name){const data=new FormData();data.append('file',file);if(name)data.append('worksheet',name);return requestJson('/pqpr/api/import-excel',{method:'POST',body:data});}
            result=await readSheet();
            if(result.status==='choose_sheet'){const name=await chooseWorksheet(result.worksheets);if(!name)return;result=await readSheet(name);}
        } else {
            let data;try{data=JSON.parse(await file.text());}catch{throw new Error('This file is not valid JSON.');}
            result=await postJson('/pqpr/api/import',{project:data});
        }
        if(!confirmReplace())return;
        loadedFilename=loadedRevision=null;savedSnapshot=JSON.stringify(result.project);
        applyProject(result.project);remember();select.value='';
        say(`Imported "${file.name}". Save or export to keep this project.`+(result.warnings?.length?' '+result.warnings.join(' '):''));
    }catch(error){say('Import failed: '+error.message,true);}finally{setBusy(false);fileInput.value='';}
});
document.getElementById('pqpr-export').addEventListener('click',async()=>{
    setBusy(true);
    try {
        const data=await postJson('/pqpr/api/export',{project,filename:loadedFilename||project.project_name});
        const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)+'\n'],{type:'application/json'}));
        const link=document.createElement('a');link.href=url;link.download=loadedFilename||(project.project_name.replace(/[^A-Za-z0-9_-]+/g,'_')||'pqpr_project')+'.json';
        document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
        say('Exported PQPR project as JSON.');
    }catch(error){say(error.message,true);}finally{setBusy(false);}
});

async function init() {
    setBusy(true);
    try {
        const draft=JSON.parse(sessionStorage.getItem(draftKey)||'null');
        if(draft?.project){const data=await postJson('/pqpr/api/import',{project:draft.project});
            project=data.project;loadedFilename=draft.loadedFilename||null;loadedRevision=draft.loadedRevision||null;savedSnapshot=draft.savedSnapshot||JSON.stringify(project);}
        await refreshFiles();
    }catch(error){say('Could not restore the PQPR draft: '+error.message,true);
        const previous=sessionStorage.getItem(draftKey);if(previous)sessionStorage.setItem(draftKey+'-unrestored',previous);
    }finally{render();setBusy(false);app.dataset.ready='true';}
    window.addEventListener('pagehide',remember);
}
init();
