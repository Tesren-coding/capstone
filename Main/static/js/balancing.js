import {escapeHtml as esc} from './canvas-tools.js';
import {requestJson,postJson} from './api.js';
import {blankPlan,activeStep,activeProcess,assignmentMap,assignStep,addOperator,addProcess,removeProcess,addStep,removeStep,placeStep,analysePlan,timeText,valueClasses,processColors,valueColors} from './balancing-model.js';
import {installLineLayout} from './line-layout.js';
import {yamazumiSvg,chartDrop} from './yamazumi.js';
import {installDrag,dragHandle,moveBefore,rowDrop,beforeFromDrop} from './drag-sort.js';

const app=document.getElementById('balance-app'),version=Number(app.dataset.schemaVersion);
const status=document.getElementById('balance-status'),workspace=document.getElementById('balance-workspace');
const rows=document.getElementById('balance-steps'),operators=document.getElementById('balance-operators');
const processRows=document.getElementById('balance-processes');
const chart=document.getElementById('balance-chart'),sourceSelect=document.getElementById('balance-source-select');
const frameSelect=document.getElementById('balance-frame-select'),savedSelect=document.getElementById('balance-plan-select');
const draftKey='capstone-balancing-draft';
let plan=blankPlan(version),candidate=null,loadedFilename=null,loadedRevision=null,savedSnapshot=JSON.stringify(plan),busy=false;
const categoryNames={in_line:'In line',out_of_line:'Out of line',unique:'Low hit rate / unique'};
const reportNames={within_takt:'Within takt',over_takt:'Above takt',incomplete:'Incomplete',no_steps:'No steps'};
const pct=value=>value===null?'—':`${Number(value.toFixed(1))}%`;

function say(message,error=false){status.textContent=message;status.classList.toggle('balance-message--error',error);}
function setBusy(value){busy=value;workspace.disabled=value;app.querySelectorAll('[data-file-action]').forEach(c=>c.disabled=value);}
function dirty(){return JSON.stringify(plan)!==savedSnapshot;}
function remember(){try{sessionStorage.setItem(draftKey,JSON.stringify({plan,loadedFilename,loadedRevision,savedSnapshot}));}catch{say('Draft cannot be kept in this browser. Save or export your plan.',true);}}
function confirmReplace(){return !dirty()||confirm('Replace your unsaved balancing plan?');}
function notifyChanged(){update();remember();}
function operatorOptions(selected){return '<option value="">Unassigned</option>'+plan.operators.map(op=>`<option value="${op.id}" ${selected===op.id?'selected':''}>${esc(op.name)} (${op.id})</option>`).join('');}

const lineLayout=installLineLayout(document.getElementById('balance-line-layout'),{
    items:()=>plan.processes.filter(p=>activeProcess(plan,p)).map((p,index)=>({id:p.id,name:p.name,label:'S'+(index+1)})),
    selection:()=>plan.line_layout?.break_after_process_id||plan.steps.find(s=>s.id===plan.line_layout?.break_after_step_id)?.balance_process_id||null,
    change:id=>{plan.line_layout={shape:'c',break_after_process_id:id};notifyChanged();say('C-shaped row break saved in this plan. Build Line setup will use it.');}
});

function processOptions(selected){return plan.processes.map(p=>`<option value="${p.id}" ${p.id===selected?'selected':''}>${esc(p.name)}</option>`).join('');}
function renderProcesses(){
    processRows.innerHTML=plan.processes.map((p,index)=>{
        const elements=plan.steps.filter(s=>s.balance_process_id===p.id),sum=field=>elements.some(s=>s[field]===null)?null:elements.reduce((total,s)=>total+s[field],0);
        return `<tr data-balance-process-row="${p.id}" class="${activeProcess(plan,p)?'':'balance-step-excluded'}"><td>${dragHandle('balance-process',p.id,p.name)}${index+1}</td><td><input data-parent-process="${p.id}" data-field="name" value="${esc(p.name)}" aria-label="Parent process ${index+1} name"><select data-parent-process="${p.id}" data-field="category" aria-label="${esc(p.name+' process category')}">${Object.entries(categoryNames).map(([key,name])=>`<option value="${key}" ${p.category===key?'selected':''}>${name}</option>`).join('')}</select></td><td><label class="balance-case"><input type="checkbox" data-parent-process="${p.id}" data-field="included" ${p.included?'checked':''} ${p.applicability==='required'?'disabled':''}>Include</label><select data-parent-process="${p.id}" data-field="applicability" aria-label="${esc(p.name+' process applicability')}"><option value="required" ${p.applicability==='required'?'selected':''}>Always</option><option value="optional" ${p.applicability==='optional'?'selected':''}>Sometimes</option></select></td><td><input type="number" min="0" step="any" data-parent-process="${p.id}" data-field="manual_time" value="${p.manual_time??''}" placeholder="Unknown" aria-label="${esc(p.name+' process manual minutes')}"></td><td><input type="number" min="0" step="any" data-parent-process="${p.id}" data-field="auto_time" value="${p.auto_time??0}" placeholder="0" aria-label="${esc(p.name+' process automatic minutes')}"></td><td><strong>${elements.length} working elements</strong><small>${elements.length?'Element sums: M '+timeText(sum('manual_time'))+' · A '+timeText(sum('auto_time')):'Add its breakdown before balancing.'}</small></td><td class="balance-process-actions"><button data-add-element="${p.id}">+ Working element</button>${!elements.length?`<button data-use-process="${p.id}">Use as one element</button>`:''}<button data-remove-process="${p.id}">Remove process</button></td></tr>`;
    }).join('')||'<tr><td colspan="7" class="balance-empty">Add a process or import a framesize from PQPR, then break it into working elements.</td></tr>';
    const chooser=document.getElementById('balance-element-process'),selected=chooser.value;chooser.innerHTML=processOptions(selected);
}
function renderSteps(){
    const assigned=assignmentMap(plan);
    if(!plan.steps.length){rows.innerHTML='<tr><td colspan="8" class="balance-empty">Processes appear above. Add their working elements to assign work and build the Yamazumi.</td></tr>';return;}
    rows.innerHTML=plan.steps.map((step,index)=>{
        const active=activeStep(plan,step);
        return `<tr data-step-row="${step.id}" class="${active?'':'balance-step-excluded'}"><td>${dragHandle('balance-step',step.id,step.name,'data-drag-area="route"')}${index+1}<small>${esc(step.id)}</small></td><td><input data-step="${step.id}" data-field="name" value="${esc(step.name)}" aria-label="Working element ${index+1} name"><select data-step="${step.id}" data-field="balance_process_id" aria-label="${esc(step.name+' parent process')}">${processOptions(step.balance_process_id)}</select><select data-step="${step.id}" data-field="category" aria-label="${esc(step.name+' category')}">${Object.entries(categoryNames).map(([key,name])=>`<option value="${key}" ${step.category===key?'selected':''}>${name}</option>`).join('')}</select></td><td><label class="balance-case"><input type="checkbox" data-step="${step.id}" data-field="included" aria-label="${esc(step.name+' included in this case')}" ${step.included?'checked':''} ${step.applicability==='required'?'disabled':''}>Include</label><select data-step="${step.id}" data-field="applicability" aria-label="${esc(step.name+' applicability')}"><option value="required" ${step.applicability==='required'?'selected':''}>Always</option><option value="optional" ${step.applicability==='optional'?'selected':''}>Sometimes</option></select>${!plan.include_out_of_line&&step.category==='out_of_line'?'<small>Outside scope</small>':''}</td><td><input type="number" min="0" step="any" data-step="${step.id}" data-field="manual_time" value="${step.manual_time??''}" placeholder="Unknown" aria-label="${esc(step.name+' manual minutes')}"></td><td><input type="number" min="0" step="any" data-step="${step.id}" data-field="auto_time" value="${step.auto_time??0}" placeholder="0" aria-label="${esc(step.name+' automatic minutes')}"></td><td><select data-step="${step.id}" data-field="operator" ${active?'':'disabled'} aria-label="${esc(step.name+' assigned operator')}">${operatorOptions(assigned[step.id])}</select></td><td><select data-step="${step.id}" data-field="value_class" aria-label="${esc(step.name+' value classification')}">${Object.entries(valueClasses).map(([key,name])=>`<option value="${key}" ${step.value_class===key?'selected':''}>${name}</option>`).join('')}</select></td><td><button data-remove-step="${step.id}">Remove</button></td></tr>`;
    }).join('');
}
function renderOperators(analysis){
    const byId=Object.fromEntries(plan.steps.map(s=>[s.id,s]));
    operators.innerHTML=plan.operators.length?plan.operators.map((op,index)=>{
        const report=analysis.operators[index];
        return `<article class="balance-operator-card" data-operator-card="${op.id}"><div class="balance-operator-heading"><input data-operator="${op.id}" data-field="name" value="${esc(op.name)}" aria-label="Operator ${index+1} name"><span class="balance-operator-id">${op.id}</span>${dragHandle('balance-operator',op.id,op.name)}<button data-operator-action="remove" data-id="${op.id}">Remove</button></div><div class="balance-operator-totals"><strong>Manual ${timeText(report.manual_time)}</strong><span>Auto ${timeText(report.auto_time)} (process sum)</span><span>Manual / takt ${pct(report.utilization)}</span><span class="balance-report balance-report--${report.status}">${reportNames[report.status]}</span></div><ol data-sequence-operator="${op.id}">${op.sequence.map((id,i)=>{const step=byId[id];return `<li data-sequence-step="${id}" class="${activeStep(plan,step)?'':'balance-sequence-excluded'}"><span>${esc(step.name)}<small>${activeStep(plan,step)?timeText(step.manual_time)+' manual':'Excluded from this case / scope'}</small></span>${dragHandle('balance-step',id,step.name,'data-drag-area="sequence"')}<button data-sequence-action="unassign" data-operator="${op.id}" data-step="${id}" aria-label="Unassign ${esc(step.name)}">×</button></li>`;}).join('')||'<li class="balance-empty">Drop a work step here, or assign it from the process table.</li>'}</ol></article>`;
    }).join(''):'<div class="balance-empty">Add your operators, then assign their working elements below.</div>';
}
function renderChart(analysis){
    const labels=plan.chart_color_mode==='process'?categoryNames:valueClasses,colors=plan.chart_color_mode==='process'?processColors:valueColors;
    document.getElementById('balance-chart-legend').innerHTML=Object.entries(labels).map(([key,name])=>`<span><i style="background:${colors[key]}"></i>${name}</span>`).join('')+'<span><i class="balance-takt-key"></i>Takt time</span>';
    chart.innerHTML=yamazumiSvg(plan,analysis)||'<div class="balance-empty">Add operators to display their Yamazumi bars.</div>';
    document.getElementById('balance-export-chart').disabled=!plan.operators.length;
}
function update({keepOperators=false,keepProcesses=false}={}){
    const analysis=analysePlan(plan);
    document.getElementById('balance-active-count').textContent=analysis.active_steps;
    document.getElementById('balance-unassigned-count').textContent=analysis.unassigned.length;
    document.getElementById('balance-over-count').textContent=analysis.operators.filter(op=>op.status==='over_takt').length;
    document.getElementById('balance-efficiency').textContent=pct(analysis.balance_efficiency);
    document.getElementById('balance-min-operators').textContent=analysis.active_steps?(analysis.minimum_operators??'—'):'—';
    document.getElementById('balance-draft-state').textContent=dirty()?'Unsaved changes':loadedFilename?'Saved · '+loadedFilename:'New / copied plan';
    const notes=[];
    if(analysis.processes_without_elements.length)notes.push(`${analysis.processes_without_elements.length} in-scope process(es) need working elements. Their process totals are not counted as operator work.`);
    if(analysis.unassigned.length)notes.push(`${analysis.unassigned.length} in-scope step(s) need an operator.`);
    if(analysis.unknown_manual.length)notes.push(`${analysis.unknown_manual.length} manual time(s) are unknown. Chart bars show known time only.`);
    if(analysis.unknown_auto.length)notes.push(`${analysis.unknown_auto.length} automatic time(s) are unknown; manual workload can still be assessed.`);
    if(plan.takt_time===null)notes.push('Set takt time to compare workloads.');
    if(analysis.balance_efficiency!==null)notes.push(`Balance efficiency = total manual ÷ (operator count × largest manual workload). Takt load: ${pct(analysis.takt_load)}.`);
    if(analysis.active_steps)notes.push('Minimum operators is a manual-time lower bound. Walking, waiting, precedence and machines may require more.');
    document.getElementById('balance-analysis-note').textContent=notes.join(' ');
    if(!keepOperators)renderOperators(analysis);
    if(!keepProcesses)renderProcesses();
    renderChart(analysis);lineLayout.render();
    if(plan.source){const frame=plan.source.project.framesizes.find(f=>f.id===plan.framesize_id);document.getElementById('balance-active-source').textContent=`Active plan: ${plan.source.project.project_name} / ${frame.name}${frame.stage?' / Stage '+frame.stage:''} · ${plan.parts_per_set} parts per set. Process timings are per part; assign their working elements below.`;}
    else document.getElementById('balance-active-source').textContent='Independent plan. Add and edit processes below.';
    document.getElementById('balance-clear-assignments').disabled=!plan.operators.some(op=>op.sequence.length);
}
function render(){
    document.getElementById('balance-plan-name').value=plan.plan_name;
    document.getElementById('balance-takt').value=plan.takt_time??'';
    document.getElementById('balance-out-of-line').checked=plan.include_out_of_line;
    document.getElementById('balance-color-mode').value=plan.chart_color_mode;
    document.getElementById('balance-parts-per-set').value=plan.parts_per_set;
    renderSteps();update();
}
function setCandidate(data,selectedFrame=null){
    candidate=data;document.getElementById('balance-source-panel').open=true;
    frameSelect.replaceChildren(...data.project.framesizes.map(f=>new Option(`${f.name}${f.stage?' / Stage '+f.stage:''}${f.component?' / '+f.component:''}`,f.id)));
    if(selectedFrame)frameSelect.value=selectedFrame;
    frameSelect.disabled=!data.project.framesizes.length;
    document.getElementById('balance-create').disabled=!data.project.framesizes.length;
    document.getElementById('balance-source-preview').textContent=`Selected source: ${data.project.project_name}. Choose a framesize and Create plan to use this copy. This replaces the current process list and assignments.`;
}
function applyPlan(data){plan=structuredClone(data);candidate=null;if(plan.source)setCandidate(plan.source,plan.framesize_id);else resetCandidate();render();}
function resetCandidate(){candidate=null;frameSelect.replaceChildren(new Option('Load a PQPR project first',''));frameSelect.disabled=true;document.getElementById('balance-create').disabled=true;document.getElementById('balance-source-preview').textContent='Load a saved PQPR project, its current-tab draft, or a PQPR JSON file.';}
async function refreshFiles(){
    const plans=await requestJson('/line-balancing/api/plans');
    savedSelect.replaceChildren(new Option('Select saved plan',''));plans.files.forEach(name=>savedSelect.add(new Option(name.replace(/\.json$/,''),name)));if(loadedFilename)savedSelect.value=loadedFilename;
}
async function refreshSources(){
    try{const projects=await requestJson('/pqpr/api/projects');sourceSelect.replaceChildren(new Option('Select a saved PQPR project',''));projects.files.forEach(name=>sourceSelect.add(new Option(name.replace(/\.json$/,''),name)));}
    catch(error){say('PQPR source list unavailable. Your independent plan can still be edited. '+error.message,true);}
}
document.getElementById('balance-source-panel').addEventListener('toggle',()=>{if(document.getElementById('balance-source-panel').open)refreshSources();});
async function useDraft(){
    const draft=JSON.parse(sessionStorage.getItem('capstone-pqpr-draft')||'null');
    if(!draft?.project)throw new Error('No PQPR draft exists in this tab. Open PQPR, create/import a project, then return here.');
    const data=await postJson('/pqpr/api/import',{project:draft.project});
    setCandidate({project:data.project,filename:null,revision:null});say('PQPR draft loaded. Select a framesize and create the plan.');
}

document.getElementById('balance-use-draft').addEventListener('click',async()=>{setBusy(true);try{await useDraft();}catch(error){say(error.message,true);}finally{setBusy(false);}});
document.getElementById('balance-use-saved').addEventListener('click',async()=>{
    if(!sourceSelect.value){say('Select a saved PQPR project.');return;}setBusy(true);
    try{const data=await requestJson('/pqpr/api/projects/'+encodeURIComponent(sourceSelect.value));if(!data.found)throw new Error('PQPR project no longer exists.');setCandidate({project:data.project,filename:data.filename,revision:data.revision});say('PQPR project loaded. Select a framesize and create the plan.');}
    catch(error){say(error.message,true);}finally{setBusy(false);}
});
const pqprFile=document.getElementById('balance-pqpr-file');
document.getElementById('balance-import-pqpr').addEventListener('click',()=>pqprFile.click());
pqprFile.addEventListener('change',async()=>{const file=pqprFile.files[0];if(!file)return;setBusy(true);try{let project;try{project=JSON.parse(await file.text());}catch{throw new Error('This file is not valid JSON.');}const data=await postJson('/pqpr/api/import',{project});setCandidate({project:data.project,filename:null,revision:null});say('PQPR JSON loaded. Select a framesize and create the plan.');}catch(error){say(error.message,true);}finally{setBusy(false);pqprFile.value='';}});
document.getElementById('balance-create').addEventListener('click',async()=>{
    if(!candidate||!frameSelect.value)return;if(!confirmReplace())return;setBusy(true);
    try{const data=await postJson('/line-balancing/api/from-pqpr',{...candidate,framesize_id:frameSelect.value});loadedFilename=loadedRevision=null;savedSnapshot=JSON.stringify(data.plan);applyPlan(data.plan);remember();say('Processes copied from PQPR with this framesize’s times and parts per set. Break them into working elements, then assign operators.');}
    catch(error){say(error.message,true);}finally{setBusy(false);}
});
document.getElementById('balance-plan-name').addEventListener('input',event=>{plan.plan_name=event.target.value;notifyChanged();});
document.getElementById('balance-takt').addEventListener('input',event=>{plan.takt_time=event.target.value===''?null:Number(event.target.value);notifyChanged();});
document.getElementById('balance-out-of-line').addEventListener('change',event=>{plan.include_out_of_line=event.target.checked;renderSteps();notifyChanged();});
document.getElementById('balance-color-mode').addEventListener('change',event=>{plan.chart_color_mode=event.target.value;notifyChanged();});
function createElement(parentId,useProcessTimes=false){const step=addStep(plan,parentId,{useProcessTimes});renderSteps();notifyChanged();const input=rows.querySelector(`[data-step="${step.id}"][data-field="name"]`);input.focus();input.select();}
document.getElementById('balance-add-step').addEventListener('click',()=>createElement(document.getElementById('balance-element-process').value));
document.getElementById('balance-add-process').addEventListener('click',()=>{const p=addProcess(plan);notifyChanged();const input=processRows.querySelector(`[data-parent-process="${p.id}"][data-field="name"]`);input.focus();input.select();});
document.getElementById('balance-parts-per-set').addEventListener('input',event=>{plan.parts_per_set=event.target.value===''?null:Number(event.target.value);notifyChanged();});
processRows.addEventListener('input',event=>{
    const input=event.target;if(!input.dataset.parentProcess||!['name','manual_time','auto_time'].includes(input.dataset.field))return;
    const p=plan.processes.find(p=>p.id===input.dataset.parentProcess);p[input.dataset.field]=input.dataset.field==='name'?input.value:input.dataset.field==='auto_time'?Number(input.value):input.value===''?null:Number(input.value);
    if(input.dataset.field==='name')renderSteps();update({keepProcesses:true});remember();
});
processRows.addEventListener('change',event=>{
    if(event.target.dataset.field==='auto_time'&&event.target.value===''){event.target.value='0';return;}
    const input=event.target;if(!input.dataset.parentProcess||!['category','applicability','included'].includes(input.dataset.field))return;
    const p=plan.processes.find(p=>p.id===input.dataset.parentProcess);p[input.dataset.field]=input.dataset.field==='included'?input.checked:input.value;
    if(p.applicability==='required')p.included=true;
    plan.steps.filter(s=>s.balance_process_id===p.id).forEach(s=>{if(input.dataset.field==='category')s.category=p.category;});renderSteps();notifyChanged();
});
processRows.addEventListener('click',event=>{
    const b=event.target.closest('button');if(!b)return;
    if(b.dataset.addElement)createElement(b.dataset.addElement);
    else if(b.dataset.useProcess)createElement(b.dataset.useProcess,true);
    else if(b.dataset.removeProcess){const p=plan.processes.find(p=>p.id===b.dataset.removeProcess);if(!confirm(`Remove "${p.name}" and its working elements and assignments?`))return;removeProcess(plan,p.id);renderSteps();notifyChanged();}
});
rows.addEventListener('click',event=>{const button=event.target.closest('[data-remove-step]');if(!button)return;const step=plan.steps.find(s=>s.id===button.dataset.removeStep);if(!confirm(`Remove "${step.name}" from this plan and its operator assignments?`))return;removeStep(plan,step.id);renderSteps();notifyChanged();});
document.getElementById('balance-add-operator').addEventListener('click',()=>{const op=addOperator(plan);renderSteps();notifyChanged();const input=operators.querySelector(`[data-operator="${op.id}"][data-field="name"]`);input.focus();input.select();});
rows.addEventListener('input',event=>{
    const input=event.target;if(!input.dataset.step||!['manual_time','auto_time','name'].includes(input.dataset.field))return;
    plan.steps.find(step=>step.id===input.dataset.step)[input.dataset.field]=input.dataset.field==='name'?input.value:input.dataset.field==='auto_time'?Number(input.value):input.value===''?null:Number(input.value);notifyChanged();
});
rows.addEventListener('change',event=>{
    if(event.target.dataset.field==='auto_time'&&event.target.value===''){event.target.value='0';return;}
    const input=event.target;if(!input.dataset.step)return;const step=plan.steps.find(s=>s.id===input.dataset.step);
    if(input.dataset.field==='operator')assignStep(plan,step.id,input.value);
    else if(input.dataset.field==='balance_process_id'){const p=plan.processes.find(p=>p.id===input.value);step.balance_process_id=p.id;step.process_id=p.pqpr_process_id;step.category=p.category;renderSteps();}
    else if(input.dataset.field==='included'){step.included=input.checked;renderSteps();}
    else if(input.dataset.field==='category'){step.category=input.value;renderSteps();}
    else if(input.dataset.field==='applicability'){step.applicability=input.value;if(input.value==='required')step.included=true;renderSteps();}
    else if(input.dataset.field==='value_class')step.value_class=input.value;
    else return;notifyChanged();
});
operators.addEventListener('input',event=>{
    const input=event.target;if(input.dataset.field!=='name')return;
    const op=plan.operators.find(op=>op.id===input.dataset.operator);op.name=input.value;
    rows.querySelectorAll('select[data-field="operator"]').forEach(select=>{const value=select.value;select.innerHTML=operatorOptions(value);});
    update({keepOperators:true});remember();
});
operators.addEventListener('click',event=>{
    const button=event.target.closest('button');if(!button)return;
    if(button.dataset.operatorAction==='remove'){
        const index=plan.operators.findIndex(op=>op.id===button.dataset.id);
        if(!confirm(`Remove "${plan.operators[index].name}"? Its steps will become unassigned.`))return;
        plan.operators.splice(index,1);renderSteps();notifyChanged();
    }else if(button.dataset.sequenceAction==='unassign'){
        assignStep(plan,button.dataset.step,'');renderSteps();notifyChanged();
    }
});
document.getElementById('balance-clear-assignments').addEventListener('click',()=>{if(!confirm('Unassign all steps from operators?'))return;plan.operators.forEach(op=>op.sequence=[]);renderSteps();notifyChanged();});

installDrag(app,{
    source(node){
        if(busy)return null;
        const type=node.dataset.dragType,id=node.dataset.dragId;
        if(type==='balance-operator')return {type,id,label:plan.operators.find(op=>op.id===id).name};
        if(type==='balance-process')return {type,id,label:plan.processes.find(p=>p.id===id).name};
        if(type==='balance-step'){
            const step=plan.steps.find(s=>s.id===id);
            return {type,id,area:node.dataset.dragArea,label:step.name,active:activeStep(plan,step)};
        }return null;
    },
    target(hit,event,data){
        if(data.type==='balance-process'){const row=hit.closest('[data-balance-process-row]');return row?{...rowDrop(row,event.clientY),kind:'process',id:row.dataset.balanceProcessRow}:null;}
        if(data.type==='balance-operator'){
            const card=hit.closest('[data-operator-card]');if(!card)return null;
            return {...rowDrop(card,event.clientY),kind:'operator',id:card.dataset.operatorCard};
        }
        if(hit.closest('#balance-unassigned-drop'))return {node:document.getElementById('balance-unassigned-drop'),kind:'unassign'};
        const row=hit.closest('[data-step-row]');
        if(row&&data.area==='route')return {...rowDrop(row,event.clientY),kind:'route',id:row.dataset.stepRow};
        if(!data.active)return null;
        const chartTarget=chartDrop(chart,hit,event,plan);if(chartTarget)return {...chartTarget,kind:'work'};
        const list=hit.closest('[data-sequence-operator]'),card=hit.closest('[data-operator-card]');
        if(list||card){const opId=list?.dataset.sequenceOperator||card.dataset.operatorCard;
            const item=hit.closest('[data-sequence-step]');
            const where=item?rowDrop(item,event.clientY):{node:list||card,after:true};
            const op=plan.operators.find(op=>op.id===opId);
            return {...where,kind:'work',operatorId:opId,beforeId:item?beforeFromDrop(op.sequence,item.dataset.sequenceStep,where.after,id=>id):null};
        }return null;
    },
    drop(data,where){
        if(where.kind==='process')moveBefore(plan.processes,data.id,beforeFromDrop(plan.processes,where.id,where.after));
        else if(where.kind==='operator')moveBefore(plan.operators,data.id,beforeFromDrop(plan.operators,where.id,where.after));
        else if(where.kind==='route')moveBefore(plan.steps,data.id,beforeFromDrop(plan.steps,where.id,where.after));
        else placeStep(plan,data.id,where.kind==='unassign'?'':where.operatorId,where.beforeId);
        renderSteps();notifyChanged();say('Work order and workloads updated.');
    },
    keyboard(data,key){
        const direction=['ArrowUp','ArrowLeft'].includes(key)?-1:1;
        const list=data.type==='balance-process'?plan.processes:data.type==='balance-operator'?plan.operators:data.area==='route'?plan.steps:plan.operators.find(op=>op.sequence.includes(data.id))?.sequence;
        if(!list)return;const getId=item=>typeof item==='string'?item:item.id;
        const index=list.findIndex(item=>getId(item)===data.id),other=index+direction;
        if(other<0||other>=list.length)return;[list[index],list[other]]=[list[other],list[index]];
        renderSteps();notifyChanged();app.querySelector(`[data-drag-id="${data.id}"][data-drag-type="${data.type}"]${data.area?'[data-drag-area="'+data.area+'"]':''}`)?.focus();
    }
});

function chartDetail(target,select=false){
    const node=target.closest('[data-step]');if(!node)return;const step=plan.steps.find(s=>s.id===node.getAttribute('data-step'));
    const op=plan.operators.find(op=>op.sequence.includes(step.id));document.getElementById('balance-chart-info').textContent=`${op.name} / ${step.name} · Manual ${timeText(step.manual_time)} · Auto ${timeText(step.auto_time)} · ${valueClasses[step.value_class]}`;
    if(select){const row=rows.querySelector(`[data-step-row="${step.id}"]`);rows.querySelectorAll('.balance-row-selected').forEach(r=>r.classList.remove('balance-row-selected'));row.classList.add('balance-row-selected');row.scrollIntoView({block:'center',behavior:'smooth'});row.querySelector('select[data-field="operator"]').focus({preventScroll:true});}
}
chart.addEventListener('mouseover',event=>chartDetail(event.target));chart.addEventListener('focusin',event=>chartDetail(event.target));chart.addEventListener('click',event=>chartDetail(event.target,true));chart.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();chartDetail(event.target,true);}});
function download(data,mime,filename){const url=URL.createObjectURL(new Blob([data],{type:mime}));const link=document.createElement('a');link.href=url;link.download=filename;document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function exportName(extension){return (plan.plan_name.replace(/[^A-Za-z0-9_-]+/g,'_')||'balancing_plan')+'.'+extension;}
document.getElementById('balance-export-chart').addEventListener('click',()=>{const svg=chart.querySelector('svg');if(svg)download('<?xml version="1.0" encoding="UTF-8"?>\n'+svg.outerHTML,'image/svg+xml',exportName('svg'));});
document.getElementById('balance-new').addEventListener('click',()=>{if(busy||!confirmReplace())return;loadedFilename=loadedRevision=null;plan=blankPlan(version);savedSnapshot=JSON.stringify(plan);resetCandidate();render();remember();say('New independent plan. Add processes, their working elements and operators.');});
function chooseSave(filename){return new Promise(resolve=>{const dialog=document.getElementById('balance-save-dialog');document.getElementById('balance-save-message').textContent=`Save changes to "${filename}" or create a numbered copy?`;const finish=mode=>{dialog.close();resolve(mode);};dialog.querySelectorAll('[data-save-mode]').forEach(b=>b.onclick=()=>finish(b.dataset.saveMode==='cancel'?null:b.dataset.saveMode));dialog.oncancel=event=>{event.preventDefault();finish(null);};dialog.showModal();});}
document.getElementById('balance-save').addEventListener('click',async()=>{
    setBusy(true);try{const snapshot=structuredClone(plan);let filename=loadedFilename,mode=filename?await chooseSave(filename):'create';if(!mode)return;
        async function submit(){const response=await fetch('/line-balancing/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({plan:snapshot,name:snapshot.plan_name,filename,mode,expected_revision:filename===loadedFilename?loadedRevision:null})});return response.json();}
        let data=await submit();if(data.status==='exists'){filename=data.filename;mode=await chooseSave(filename);if(!mode)return;data=await submit();}
        if(data.status!=='saved')throw new Error(data.errors?.join('\n')||data.error||'Could not save plan.');loadedFilename=data.filename;loadedRevision=data.revision;savedSnapshot=JSON.stringify(snapshot);notifyChanged();await refreshFiles();say(`Saved "${loadedFilename}".`);
    }catch(error){say(error.message,true);}finally{setBusy(false);}
});
document.getElementById('balance-load').addEventListener('click',async()=>{if(!savedSelect.value){say('Choose a saved balancing plan.');return;}setBusy(true);try{const data=await requestJson('/line-balancing/api/plans/'+encodeURIComponent(savedSelect.value));if(!data.found)throw new Error('Plan no longer exists.');if(!confirmReplace())return;loadedFilename=data.filename;loadedRevision=data.revision;savedSnapshot=JSON.stringify(data.plan);applyPlan(data.plan);remember();say(`Loaded "${loadedFilename}".`);}catch(error){say(error.message,true);}finally{setBusy(false);}});
const planFile=document.getElementById('balance-plan-file');document.getElementById('balance-import').addEventListener('click',()=>planFile.click());
planFile.addEventListener('change',async()=>{const file=planFile.files[0];if(!file)return;setBusy(true);try{let original;try{original=JSON.parse(await file.text());}catch{throw new Error('This file is not valid JSON.');}const data=await postJson('/line-balancing/api/import',{plan:original});if(!confirmReplace())return;loadedFilename=loadedRevision=null;savedSnapshot=JSON.stringify(data.plan);applyPlan(data.plan);remember();say(`Imported "${file.name}".`);}catch(error){say('Import failed: '+error.message,true);}finally{setBusy(false);planFile.value='';}});
document.getElementById('balance-export').addEventListener('click',async()=>{setBusy(true);try{const data=await postJson('/line-balancing/api/export',{plan,filename:loadedFilename||plan.plan_name});download(JSON.stringify(data,null,2)+'\n','application/json',loadedFilename||exportName('json'));say('Exported balancing plan JSON.');}catch(error){say(error.message,true);}finally{setBusy(false);}});

async function init(){setBusy(true);try{const draft=JSON.parse(sessionStorage.getItem(draftKey)||'null');if(draft?.plan){const data=await postJson('/line-balancing/api/import',{plan:draft.plan});plan=data.plan;loadedFilename=draft.loadedFilename||null;loadedRevision=draft.loadedRevision||null;savedSnapshot=draft.savedSnapshot||JSON.stringify(plan);}await refreshFiles();applyPlan(plan);if(plan.steps.length||plan.operators.length)say('Restored the current tab’s balance plan. Continue editing or load a saved plan.');if(new URLSearchParams(location.search).get('source')==='pqpr-draft')await useDraft();}
    catch(error){say('Could not initialize balancing: '+error.message,true);const previous=sessionStorage.getItem(draftKey);if(previous)sessionStorage.setItem(draftKey+'-unrestored',previous);render();}
    finally{setBusy(false);app.dataset.ready='true';}window.addEventListener('pagehide',remember);
}
init();
