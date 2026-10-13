// Pointer sorting works for HTML lists and SVG segments, including touch.
export function moveBefore(list,id,beforeId,key=item=>item.id) {
    if(id===beforeId)return false;
    const index=list.findIndex(item=>key(item)===id);
    if(index<0)return false;
    const [item]=list.splice(index,1),target=list.findIndex(item=>key(item)===beforeId);
    list.splice(target<0?list.length:target,0,item);return true;
}
export function rowDrop(row,y) {
    const rect=row.getBoundingClientRect();
    return {node:row,after:y>rect.top+rect.height/2};
}
export function beforeFromDrop(list,id,after,key=item=>item.id) {
    const index=list.findIndex(item=>key(item)===id);
    return after?(index<list.length-1?key(list[index+1]):null):id;
}
export function dragHandle(type,id,label,extra='') {
    const safe=label.replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;').replaceAll('>','&gt;');
    return `<button type="button" class="drag-handle" data-drag-type="${type}" data-drag-id="${id}" ${extra} aria-label="Drag ${safe}; Alt+Arrow to reorder" title="Drag to reorder; Alt+Arrow keys also work">⠿</button>`;
}
export function installDrag(root,{source,target,drop,keyboard}) {
    let pending=null,ghost=null,mark=null,dragged=false,scrollFrame=0,lastPoint=null,suppressClick=false;
    function clearMark(){if(mark){mark.classList.remove('drag-over','drag-before','drag-after');mark=null;}}
    function preview(event){
        clearMark();const hit=document.elementFromPoint(event.clientX,event.clientY);
        pending.target=hit&&root.contains(hit)?target(hit,event,pending.data):null;
        if(pending.target?.node){mark=pending.target.node;mark.classList.add('drag-over',pending.target.after?'drag-after':'drag-before');}
    }
    function autoscroll(){
        if(!pending||!dragged)return;
        const hit=document.elementFromPoint(lastPoint.clientX,lastPoint.clientY);
        let node=hit;
        while(node&&node!==document.body){
            const style=getComputedStyle(node),rect=node.getBoundingClientRect();
            const dy=lastPoint.clientY<rect.top+30?-10:lastPoint.clientY>rect.bottom-30?10:0;
            const dx=lastPoint.clientX<rect.left+30?-10:lastPoint.clientX>rect.right-30?10:0;
            if((/auto|scroll/.test(style.overflowY)&&node.scrollHeight>node.clientHeight&&dy)||(/auto|scroll/.test(style.overflowX)&&node.scrollWidth>node.clientWidth&&dx)){
                const oldX=node.scrollLeft,oldY=node.scrollTop;node.scrollBy(dx,dy);
                if(node.scrollLeft!==oldX||node.scrollTop!==oldY)break;
            }node=node.parentElement;
        }
        if(!node||node===document.body){if(lastPoint.clientY<45)window.scrollBy(0,-12);else if(lastPoint.clientY>innerHeight-45)window.scrollBy(0,12);}
        preview(lastPoint);scrollFrame=requestAnimationFrame(autoscroll);
    }
    function finish(commit=false){
        if(!pending)return;const data=pending.data,where=pending.target,node=pending.node;
        const wasDragged=dragged;pending=null;dragged=false;cancelAnimationFrame(scrollFrame);
        ghost?.remove();ghost=null;clearMark();document.body.classList.remove('is-sorting');node.classList.remove('is-drag-source');
        document.removeEventListener('pointermove',move);document.removeEventListener('pointerup',up);document.removeEventListener('pointercancel',cancel);
        if(wasDragged){suppressClick=true;setTimeout(()=>{suppressClick=false;},0);if(commit&&where)drop(data,where);}
    }
    function move(event){
        if(!pending||event.pointerId!==pending.pointerId)return;
        if(!dragged&&Math.hypot(event.clientX-pending.x,event.clientY-pending.y)<6)return;
        event.preventDefault();lastPoint=event;
        if(!dragged){dragged=true;document.body.classList.add('is-sorting');pending.node.classList.add('is-drag-source');ghost=document.createElement('div');ghost.className='drag-ghost';ghost.textContent=pending.data.label||'Move item';document.body.appendChild(ghost);scrollFrame=requestAnimationFrame(autoscroll);}
        ghost.style.left=Math.min(event.clientX+14,innerWidth-190)+'px';ghost.style.top=(event.clientY+12)+'px';preview(event);
    }
    const up=event=>{if(pending&&event.pointerId===pending.pointerId)finish(true);};
    const cancel=()=>finish();
    root.addEventListener('pointerdown',event=>{
        if(event.button!==0||pending)return;const node=event.target.closest('[data-drag-type]');
        if(!node||!root.contains(node)||node.matches(':disabled')||node.closest('fieldset:disabled'))return;
        const data=source(node,event);if(!data)return;
        pending={node,data,x:event.clientX,y:event.clientY,pointerId:event.pointerId,target:null};
        document.addEventListener('pointermove',move,{passive:false});document.addEventListener('pointerup',up);document.addEventListener('pointercancel',cancel);
    });
    root.addEventListener('click',event=>{if(suppressClick){event.preventDefault();event.stopImmediatePropagation();}},true);
    root.addEventListener('keydown',event=>{
        if(event.key==='Escape'&&pending){event.preventDefault();finish();return;}
        if(pending)return;
        const node=event.target.closest('[data-drag-type]');
        if(node&&keyboard&&event.altKey&&['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(event.key)){
            const data=source(node,event);if(data){event.preventDefault();keyboard(data,event.key);}
        }
    });
    window.addEventListener('blur',cancel);
}
