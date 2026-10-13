import {escapeHtml as esc} from './canvas-tools.js';
import {installDrag} from './drag-sort.js';
import {STATION_WIDTH, STATION_HEIGHT} from './layout-geometry.js';

export function breakCount(ids,afterId=null){
    if(ids.length<2)return ids.length;
    const index=ids.indexOf(afterId);
    return index>=0&&index<ids.length-1?index+1:Math.ceil(ids.length/2);
}
export function cLayout(ids,afterId=null){
    const count=breakCount(ids,afterId),positions={};
    ids.forEach((id,index)=>{positions[id]={x:80+(index<count?count-1-index:index-count)*330,y:index<count?220:620,w:STATION_WIDTH,h:STATION_HEIGHT};});
    const input={x:80+Math.max(1,count)*330,y:220,w:STATION_WIDTH,h:STATION_HEIGHT};
    const output={x:80+Math.max(1,ids.length-count)*330,y:620,w:STATION_WIDTH,h:STATION_HEIGHT};
    return {shape:'c',positions,input,output,break_after_id:count?ids[count-1]:null,top_count:count,width:Math.max(input.x,output.x)+STATION_WIDTH+80,height:620+STATION_HEIGHT+80};
}
const shorten=(value,max=20)=>value.length>max?value.slice(0,max-1)+'…':value;
export function cDiagram(items,afterId=null){
    if(!items.length)return '<p class="line-layout-empty">Add in-scope processes to preview the C-shaped line.</p>';
    const layout=cLayout(items.map(s=>s.id),afterId),prefix='c-layout-arrow';
    let svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 150 ${layout.width} ${layout.height-150}" width="${Math.max(620,layout.width*.55)}" height="380" role="img" aria-label="C-shaped line. Incoming at top right, stations leftward to the break, then rightward on the lower row to Outgoing."><defs><marker id="${prefix}" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8 Z" fill="#7187a6"/></marker></defs>`;
    const path=(d)=>`<path d="${d}" fill="none" stroke="#7187a6" stroke-width="4" marker-end="url(#${prefix})"/>`;
    const nodes=[layout.input,...items.map(s=>layout.positions[s.id]),layout.output];
    for(let i=0;i<nodes.length-1;i++){
        const a=nodes[i],b=nodes[i+1];
        if(a.y===b.y){const right=b.x>a.x;svg+=path(`M${a.x+(right?a.w:0)} ${a.y+a.h/2} L${b.x+(right?0:b.w)} ${b.y+b.h/2}`);}
        else if(a.x===b.x){svg+=path(`M${a.x+a.w/2} ${a.y+a.h} L${b.x+b.w/2} ${b.y}`);}
        else svg+=path(`M${a.x+a.w/2} ${a.y+a.h} L${a.x+a.w/2} ${b.y+b.h/2} L${b.x} ${b.y+b.h/2}`);
    }
    const box=(pos,label,name,kind,id)=>`<g ${id?`data-layout-station="${id}"`:''}><title>${esc(label+' · '+name)}</title><rect x="${pos.x}" y="${pos.y}" width="${pos.w}" height="${pos.h}" rx="12" fill="${kind==='box'?'#e6edf9':'#f1f7f0'}" stroke="${kind==='box'?'#7796bf':'#7ba472'}" stroke-width="3"/><text x="${pos.x+pos.w/2}" y="${pos.y+33}" text-anchor="middle" font-size="20" fill="#294b76" font-weight="600">${esc(label)}</text><text x="${pos.x+pos.w/2}" y="${pos.y+65}" text-anchor="middle" font-size="16" fill="#496585">${esc(shorten(name))}</text></g>`;
    svg+=box(layout.input,'IN','Incoming','box','');items.forEach(s=>{svg+=box(layout.positions[s.id],s.label,s.name,'station',s.id);});svg+=box(layout.output,'OUT','Outgoing','box','');
    svg+=`<text x="${layout.positions[layout.break_after_id].x+STATION_WIDTH/2}" y="460" text-anchor="middle" font-size="23" fill="#ad6e22">Row break ↓</text></svg>`;
    return svg;
}

// The gap strip stays fixed while hovering/dragging changes only the preview.
export function installLineLayout(root,{items,selection,change}){
    let hoverId=null;
    root.innerHTML='<div class="line-layout-toolbar"><button type="button" class="drag-handle line-break-handle" data-drag-type="line-break" data-drag-id="row-break" title="Drag this marker to a station gap; Alt+Arrow keys also work" aria-label="Drag row break between stations">⠿ Row break</button><span class="line-layout-state" role="status"></span></div><div class="line-layout-strip-wrap"><div class="line-layout-strip"></div></div><div class="line-layout-preview"></div>';
    const strip=root.querySelector('.line-layout-strip'),preview=root.querySelector('.line-layout-preview'),state=root.querySelector('.line-layout-state');
    function show(){const all=items(),ids=all.map(s=>s.id),chosen=hoverId||selection();const count=breakCount(ids,chosen);preview.innerHTML=cDiagram(all,chosen);state.textContent=!all.length?'Add in-scope processes or map physical stations to set a row break.':all.length>1?`${hoverId?'Preview':'Row break'} after ${all[count-1].label} · ${count} upper / ${all.length-count} lower`:'One station: upper row with the return to Outgoing below.';}
    function hover(id){if(id===hoverId)return;hoverId=id;show();}
    function reset(){hoverId=null;show();}
    root.addEventListener('mouseover',event=>{const gap=event.target.closest('[data-line-gap]');if(gap)hover(gap.dataset.lineGap);});
    root.addEventListener('focusin',event=>{const gap=event.target.closest('[data-line-gap]');if(gap)hover(gap.dataset.lineGap);});
    root.addEventListener('mouseleave',reset);
    root.addEventListener('click',event=>{const gap=event.target.closest('[data-line-gap]');if(gap){hoverId=null;change(gap.dataset.lineGap);}});
    document.addEventListener('pointerup',()=>queueMicrotask(reset));document.addEventListener('pointercancel',reset);
    document.addEventListener('keydown',event=>{if(event.key==='Escape')reset();});
    installDrag(root,{
        source(node){return node.dataset.dragType==='line-break'&&items().length>1?{label:'Row break'}:null;},
        target(hit){const gap=hit.closest('[data-line-gap]');if(!gap)return null;hover(gap.dataset.lineGap);return {node:gap,id:gap.dataset.lineGap};},
        drop(_,where){hoverId=null;change(where.id);},
        keyboard(_,key){const all=items();if(all.length<2)return;const current=breakCount(all.map(s=>s.id),selection())-1,next=Math.max(0,Math.min(all.length-2,current+(['ArrowLeft','ArrowUp'].includes(key)?-1:1)));hoverId=null;change(all[next].id);root.querySelector('.line-break-handle').focus();}
    });
    return {render(){hoverId=null;const all=items(),count=breakCount(all.map(s=>s.id),selection());strip.innerHTML=all.map((s,index)=>`<span class="line-layout-token"><strong>${esc(s.label)}</strong><span title="${esc(s.name)}">${esc(s.name)}</span></span>${index<all.length-1?`<button type="button" class="line-layout-gap ${index===count-1?'line-layout-gap--selected':''}" data-line-gap="${s.id}" aria-label="Break after ${esc(s.label)}" aria-pressed="${index===count-1}"><span>↓</span><small>Break here</small></button>`:''}`).join('');root.querySelector('.line-break-handle').disabled=all.length<2;show();}};
}
