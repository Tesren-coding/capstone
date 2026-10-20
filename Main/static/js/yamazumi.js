import {escapeHtml as esc} from './canvas-tools.js';
import {activeStep, processColors, valueColors} from './balancing-model.js';

const short = (text,length=18) => text.length>length?text.slice(0,length-1)+'…':text;
const rounded = value => Number(value.toFixed(3));

export function yamazumiSvg(plan,analysis) {
    if(!plan.operators.length)return '';
    const width=Math.max(780,100+plan.operators.length*150),height=410;
    const left=70,right=width-30,baseline=315,top=75;
    const maximum=Math.max(1,plan.takt_time||0,...analysis.operators.map(op=>op.known_manual_time))*1.2;
    const scale=(baseline-top)/maximum;
    const byId=Object.fromEntries(plan.steps.map(step=>[step.id,step]));
    const spacing=(right-left)/plan.operators.length;
    let svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" data-baseline="${baseline}" data-time-scale="${scale}" role="group" aria-labelledby="yamazumi-title yamazumi-description" font-family="Segoe UI,Arial,sans-serif"><title id="yamazumi-title">${esc(plan.plan_name)} — manual workload chart</title><desc id="yamazumi-description">Operator manual workloads. Steps stack bottom to top in sequence order. Automatic time is excluded. Unknown manual times are marked incomplete.</desc><rect width="${width}" height="${height}" fill="#ffffff"/><text pointer-events="none" x="${left}" y="26" fill="#234978" font-size="14" font-weight="600">${esc(short(plan.plan_name,85))}</text><text pointer-events="none" x="${left}" y="48" fill="#607189" font-size="11">Manual minutes per operator · first work step at the bottom</text>`;
    for(let tick=0;tick<=5;tick++) {
        const value=maximum*tick/5,y=baseline-value*scale;
        svg+=`<line pointer-events="none" x1="${left}" x2="${right}" y1="${y}" y2="${y}" stroke="#e1e6ed"/><text pointer-events="none" x="${left-10}" y="${y+4}" fill="#607189" font-size="11" text-anchor="end">${rounded(value)}</text>`;
    }
    plan.operators.forEach((operator,index)=>{
        const report=analysis.operators[index],x=left+spacing*(index+.5),barWidth=Math.min(86,spacing*.65);
        svg+=`<g data-chart-operator="${operator.id}"><rect class="balance-bar-hit" x="${left+spacing*index}" y="${top}" width="${spacing}" height="${baseline-top+55}" fill="transparent" stroke="transparent"><title>Drop work on ${esc(operator.name)}</title></rect>`;
        let sum=0;
        operator.sequence.map(id=>byId[id]).filter(step=>activeStep(plan,step)).forEach(step=>{
            if(step.manual_time===null||step.manual_time===0)return;
            const h=step.manual_time*scale,y=baseline-(sum+step.manual_time)*scale;
            const color=plan.chart_color_mode==='value'?valueColors[step.value_class]:processColors[step.category];
            const label=`${operator.name}: ${step.name}; manual ${step.manual_time} min; automatic ${step.auto_time===null?'unknown':step.auto_time+' min'}`;
            svg+=`<g data-step="${step.id}" data-drag-type="balance-step" data-drag-id="${step.id}" data-drag-area="chart" style="touch-action:none" tabindex="0" role="button" aria-label="${esc(label)}"><title>${esc(label)}</title><rect x="${x-barWidth/2}" y="${y}" width="${barWidth}" height="${h}" fill="${color}" stroke="#ffffff" stroke-width="1"/>`;
            if(h>=28)svg+=`<text pointer-events="none" x="${x}" y="${y+h/2+4}" font-size="10" fill="#17345e" text-anchor="middle">${esc(short(step.name,11))}</text>`;
            svg+='</g>';sum+=step.manual_time;
        });
        const incomplete=report.manual_time===null;
        const label=incomplete?`${rounded(report.known_manual_time)} + ?`:`${rounded(report.manual_time)} min`;
        svg+=`<text pointer-events="none" x="${x}" y="${baseline-sum*scale-10}" fill="${report.status==='over_takt'?'#b03b46':incomplete?'#9a6b20':'#234978'}" font-size="12" text-anchor="middle" font-weight="600">${label}</text><text pointer-events="none" x="${x}" y="343" fill="#234978" font-size="12" text-anchor="middle"><title>${esc(operator.name)}</title>${esc(short(operator.name))}</text><text pointer-events="none" x="${x}" y="361" fill="#607189" font-size="10" text-anchor="middle">${esc(operator.id)} · ${report.step_count} steps</text></g>`;
    });
    if(plan.takt_time!==null) {
        const y=baseline-plan.takt_time*scale;
        svg+=`<line pointer-events="none" x1="${left}" x2="${right}" y1="${y}" y2="${y}" stroke="#c3444c" stroke-width="2" stroke-dasharray="6 4"/><text pointer-events="none" x="${right}" y="${y-7}" text-anchor="end" fill="#ad3540" font-size="11" font-weight="600">Takt ${plan.takt_time} min</text>`;
    }
    svg+=`<text pointer-events="none" x="${left}" y="393" fill="#607189" font-size="10">${analysis.unknown_manual.length?'Only known manual time is drawn; + ? marks incomplete workloads.':'Automatic time, walking and waiting are not included in these bars.'}</text></svg>`;
    return svg;
}

// SVG coordinates remain correct when the chart scales or scrolls.
export function chartDrop(chart,hit,event,plan) {
    const column=hit.closest('[data-chart-operator]');
    if(!column||!chart.contains(column))return null;
    const svg=chart.querySelector('svg'),op=plan.operators.find(op=>op.id===column.dataset.chartOperator);
    const point=new DOMPoint(event.clientX,event.clientY).matrixTransform(svg.getScreenCTM().inverse());
    const time=(Number(svg.dataset.baseline)-point.y)/Number(svg.dataset.timeScale);
    let sum=0,beforeId=null;
    for(const id of op.sequence){
        const step=plan.steps.find(s=>s.id===id);
        if(!activeStep(plan,step)||!step.manual_time)continue;
        if(time<=sum+step.manual_time/2){beforeId=id;break;}sum+=step.manual_time;
    }
    return {node:column,operatorId:op.id,beforeId,after:beforeId===null};
}
