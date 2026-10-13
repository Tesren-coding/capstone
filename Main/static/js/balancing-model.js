// Pure plan operations; Python validates the same format before persistence.
export const valueClasses = {unclassified:'Unclassified',va:'Value added',sva:'Semi value added',nva:'Non value added'};
export const processColors = {in_line:'#7ebc72',out_of_line:'#efad66',unique:'#6eb2da'};
export const valueColors = {unclassified:'#b4c1ce',va:'#6aae79',sva:'#ebc460',nva:'#dd8181'};

export function blankPlan(version=2) {
    return {document_type:'line_balance',schema_version:version,plan_name:'New balance plan',takt_time:30,
        source:null,framesize_id:null,steps:[],operators:[],next_operator_id:1,next_step_id:1,chart_color_mode:'process',include_out_of_line:false};
}
export function activeStep(plan,step) {return step.included && (plan.include_out_of_line || step.category!=='out_of_line');}
export function assignmentMap(plan) {return Object.fromEntries(plan.operators.flatMap(op=>op.sequence.map(id=>[id,op.id])));}
export function assignStep(plan,id,operatorId) {
    if(assignmentMap(plan)[id]===operatorId)return;
    plan.operators.forEach(op=>{op.sequence=op.sequence.filter(sid=>sid!==id);});
    if(operatorId)plan.operators.find(op=>op.id===operatorId).sequence.push(id);
}
export function addStep(plan) {
    let number=plan.next_step_id||1;
    while(plan.steps.some(s=>s.id==='s'+number))number++;
    plan.next_step_id=number+1;
    const step={id:'s'+number,process_id:null,name:'New process',category:'in_line',
        applicability:'required',included:true,manual_time:null,auto_time:null,value_class:'unclassified'};
    plan.steps.push(step);return step;
}
export function removeStep(plan,id) {
    plan.operators.forEach(op=>{op.sequence=op.sequence.filter(sid=>sid!==id);});
    plan.steps=plan.steps.filter(s=>s.id!==id);
}
export function placeStep(plan,id,operatorId,beforeId=null) {
    if(id===beforeId)return;
    plan.operators.forEach(op=>{op.sequence=op.sequence.filter(sid=>sid!==id);});
    if(!operatorId)return;
    const op=plan.operators.find(op=>op.id===operatorId);
    const index=op.sequence.indexOf(beforeId);
    op.sequence.splice(index<0?op.sequence.length:index,0,id);
}
export function addOperator(plan) {
    const largest=plan.operators.reduce((max,op)=>Math.max(max,Number(op.id.slice(1))||0),0);
    const number=Math.max(largest+1,plan.next_operator_id||1);
    plan.next_operator_id=number+1;
    const operator={id:'o'+number,name:'Operator '+number,sequence:[]};
    plan.operators.push(operator);return operator;
}
export function timeText(value) {return value===null?'Incomplete':`${Number(value.toFixed(3))} min`;}
export function analysePlan(plan) {
    const active=plan.steps.filter(s=>activeStep(plan,s)), byId=Object.fromEntries(plan.steps.map(s=>[s.id,s]));
    const assigned=assignmentMap(plan);
    const totalManual=active.some(s=>s.manual_time===null)?null:active.reduce((sum,s)=>sum+s.manual_time,0);
    const operators=plan.operators.map(op=>{
        const steps=op.sequence.map(id=>byId[id]).filter(s=>activeStep(plan,s));
        const manual=steps.some(s=>s.manual_time===null)?null:steps.reduce((sum,s)=>sum+s.manual_time,0);
        const automatic=steps.some(s=>s.auto_time===null)?null:steps.reduce((sum,s)=>sum+s.auto_time,0);
        return {id:op.id,name:op.name,step_count:steps.length,manual_time:manual,
            known_manual_time:steps.reduce((sum,s)=>sum+(s.manual_time||0),0),auto_time:automatic,
            utilization:manual!==null&&plan.takt_time?manual/plan.takt_time*100:null,
            status:!steps.length?'no_steps':manual===null||plan.takt_time===null?'incomplete':manual>plan.takt_time+1e-9?'over_takt':'within_takt'};
    });
    const unassigned=active.filter(s=>!assigned[s.id]).map(s=>s.id);
    const complete=!unassigned.length&&totalManual!==null&&operators.length>0&&active.length>0;
    const maximum=complete?Math.max(...operators.map(op=>op.manual_time)):null;
    const ratio=totalManual!==null&&plan.takt_time?totalManual/plan.takt_time:null;
    // Do not add an operator solely because a decimal sum rounds above an integer.
    const minimum=ratio?Math.max(1,Math.ceil(ratio-4*Number.EPSILON*ratio)):ratio===0?0:null;
    return {active_steps:active.length,unassigned,
        unknown_manual:active.filter(s=>s.manual_time===null).map(s=>s.id),unknown_auto:active.filter(s=>s.auto_time===null).map(s=>s.id),
        manual_total:totalManual,known_manual_total:active.reduce((sum,s)=>sum+(s.manual_time||0),0),operators,
        minimum_operators:minimum,
        balance_efficiency:complete&&maximum?totalManual/(operators.length*maximum)*100:null,
        takt_load:complete&&plan.takt_time?totalManual/(operators.length*plan.takt_time)*100:null};
}
