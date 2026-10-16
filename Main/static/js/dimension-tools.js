// World-coordinate station resizing and persistent canvas measurements.
// All visual sizes below are normalized by canvas zoom.
import {meterLabel} from './smart-guides.js';

export const MIN_STATION_WIDTH = 64;
export const MIN_STATION_HEIGHT = 55;
export const STATION_CORNERS = ['nw','ne','se','sw'];

export function stationCorner(station, corner) {
    return {x:station.x+(corner.includes('e')?station.w:0),
            y:station.y+(corner.includes('s')?station.h:0)};
}
export function hitStationCorner(station, point, zoom=1) {
    return STATION_CORNERS.find(c=>{
        const p=stationCorner(station,c);
        return Math.hypot(p.x-point.x,p.y-point.y)<=10/Math.max(0.05,zoom);
    })||null;
}
// The opposite corner stays fixed, regardless of which corner is dragged.
export function resizeStationRect(original,corner,moving,minimum={w:MIN_STATION_WIDTH,h:MIN_STATION_HEIGHT}) {
    const fixed=stationCorner(original,({nw:'se',ne:'sw',se:'nw',sw:'ne'})[corner]);
    const east=corner.includes('e'),south=corner.includes('s');
    const x=east?Math.max(fixed.x+minimum.w,moving.x):Math.min(fixed.x-minimum.w,moving.x);
    const y=south?Math.max(fixed.y+minimum.h,moving.y):Math.min(fixed.y-minimum.h,moving.y);
    return {x:Math.min(fixed.x,x),y:Math.min(fixed.y,y),w:Math.abs(x-fixed.x),h:Math.abs(y-fixed.y)};
}

// Anchor exactly on an object boundary (including any position along an edge),
// rather than snapping only to a corner or edge midpoint.
export function closestBoundaryPoint(point, rect) {
    const left=rect.x, right=rect.x+rect.w, top=rect.y, bottom=rect.y+rect.h;
    const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
    const c=[{x:clamp(point.x,left,right),y:top,label:'top'},
             {x:right,y:clamp(point.y,top,bottom),label:'right'},
             {x:clamp(point.x,left,right),y:bottom,label:'bottom'},
             {x:left,y:clamp(point.y,top,bottom),label:'left'}];
    return c.reduce((a,b)=>Math.hypot(point.x-a.x,point.y-a.y)<=Math.hypot(point.x-b.x,point.y-b.y)?a:b);
}
export function nearestDimensionPoint(point,items,zoom=1,tolerancePx=12) {
    let best=null;
    const tolerance=tolerancePx/Math.max(0.05,zoom);
    for(const item of items) {
        const b=item.rect;
        const cornerRadius=6/Math.max(0.05,zoom);
        const corners=[{x:b.x,y:b.y,label:'nw'},
            {x:b.x+b.w,y:b.y,label:'ne'},
            {x:b.x,y:b.y+b.h,label:'sw'},
            {x:b.x+b.w,y:b.y+b.h,label:'se'}];
        const nearCorner=corners.find(c=>Math.hypot(point.x-c.x,point.y-c.y)<=cornerRadius);
        const {x,y,label}=nearCorner||closestBoundaryPoint(point,b);
        const d=Math.hypot(point.x-x,point.y-y);
        if(d<=tolerance && (!best||d<best.distance))
            best={x,y,distance:d,anchor:{type:item.type,id:String(item.id),
                rx:b.w?(x-b.x)/b.w:0,ry:b.h?(y-b.y)/b.h:0},label};
    }
    return best||{x:point.x,y:point.y,anchor:null,label:null};
}
export function resolveDimensionPoint(d,which,findBounds) {
    const anchor=d[`${which}_anchor`];
    const bounds=anchor && findBounds(anchor.type,anchor.id);
    if(bounds) return {x:bounds.x+bounds.w*anchor.rx,y:bounds.y+bounds.h*anchor.ry};
    return which==='start'?{x:d.x,y:d.y}:{x:d.x2,y:d.y2};
}
export function resolvedDimension(d,findBounds) {
    return {start:resolveDimensionPoint(d,'start',findBounds),end:resolveDimensionPoint(d,'end',findBounds)};
}
// The measured distance is always between original anchors. Offset only moves
// the visible dimension line, leaving dotted witnesses at the original edges.
export function dimensionLinePoints(d,findBounds) {
    const {start,end}=resolvedDimension(d,findBounds);
    const dx=end.x-start.x,dy=end.y-start.y;
    const length=Math.max(0.00001,Math.hypot(dx,dy));
    const offset=Number.isFinite(d.offset)?d.offset:0;
    const nx=-dy/length,ny=dx/length;
    return {start:{x:start.x+nx*offset,y:start.y+ny*offset},
            end:{x:end.x+nx*offset,y:end.y+ny*offset},
            anchorStart:start,anchorEnd:end,nx,ny,offset};
}
export function dimensionOffsetFromDrag(d,findBounds,delta) {
    const {nx,ny,offset}=dimensionLinePoints(d,findBounds);
    return offset+delta.x*nx+delta.y*ny;
}
export function distanceFromSegment(point,start,end) {
    const dx=end.x-start.x,dy=end.y-start.y;
    const length2=dx*dx+dy*dy;
    const t=length2?Math.max(0,Math.min(1,((point.x-start.x)*dx+(point.y-start.y)*dy)/length2)):0;
    return Math.hypot(point.x-(start.x+t*dx),point.y-(start.y+t*dy));
}
export function drawDimension(ctx,d,findBounds,pixelsPerMeter,zoom=1,{selected=false,preview=false}={}) {
    const {start,end,anchorStart,anchorEnd,nx,ny}=dimensionLinePoints(d,findBounds);
    const z=Math.max(0.05,zoom);
    const dx=anchorEnd.x-anchorStart.x,dy=anchorEnd.y-anchorStart.y;
    const dist=Math.hypot(dx,dy);
    const primary=preview?'#0d9488':selected?'#1d4ed8':'#2563eb';
    ctx.save();
    // Extension / witness lines connect the object edge to the offset ruler.
    // They are always dotted, even for a selected dimension.
    ctx.strokeStyle=preview?'#5caaa4':'#7d95b6';
    ctx.lineWidth=1.05/z;
    ctx.setLineDash([3/z,4/z]);
    for(const [anchor,tip] of [[anchorStart,start],[anchorEnd,end]]) {
        if(Math.hypot(tip.x-anchor.x,tip.y-anchor.y)<0.5/z) continue;
        const ax=tip.x-anchor.x,ay=tip.y-anchor.y;
        const length=Math.hypot(ax,ay);
        ctx.beginPath();
        ctx.moveTo(anchor.x,anchor.y);
        ctx.lineTo(tip.x+ax/length*5/z,tip.y+ay/length*5/z);
        ctx.stroke();
    }
    ctx.setLineDash([]);
    ctx.strokeStyle=primary;ctx.fillStyle=primary;
    ctx.lineWidth=(selected?2:1.5)/z;
    ctx.beginPath();ctx.moveTo(start.x,start.y);ctx.lineTo(end.x,end.y);ctx.stroke();
    for(const p of [start,end]) {
        ctx.beginPath();ctx.moveTo(p.x-nx*6/z,p.y-ny*6/z);
        ctx.lineTo(p.x+nx*6/z,p.y+ny*6/z);ctx.stroke();
    }
    const mx=(start.x+end.x)/2+nx*17/z,my=(start.y+end.y)/2+ny*17/z;
    const label=meterLabel(dist,pixelsPerMeter);
    ctx.font=`${12/z}px Arial`;ctx.textAlign='center';ctx.textBaseline='middle';
    const w=ctx.measureText(label).width+12/z,h=19/z;
    ctx.fillStyle='rgba(255,255,255,.96)';ctx.fillRect(mx-w/2,my-h/2,w,h);
    ctx.strokeStyle=preview?'#5cbbb0':'#a6b8d9';ctx.lineWidth=.8/z;ctx.strokeRect(mx-w/2,my-h/2,w,h);
    ctx.fillStyle=preview?'#0f766e':'#1d4ed8';ctx.fillText(label,mx,my);
    // Endpoint controls remain on the real edges, not the shifted ruler.
    if(selected) for(const p of [anchorStart,anchorEnd]) {
        ctx.beginPath();ctx.fillStyle='#fff';ctx.strokeStyle='#1d4ed8';ctx.lineWidth=2/z;
        ctx.arc(p.x,p.y,5/z,0,2*Math.PI);ctx.fill();ctx.stroke();
    }
    ctx.restore();
}
export function drawStationDimensions(ctx,station,pixelsPerMeter,zoom=1) {
    const z=Math.max(0.05,zoom);
    const labelStyle=(label,x,y)=>{
        ctx.font=`${11/z}px Arial`;ctx.textAlign='center';ctx.textBaseline='middle';
        const width=ctx.measureText(label).width+10/z;
        ctx.fillStyle='rgba(255,255,255,.96)';ctx.fillRect(x-width/2,y-9/z,width,18/z);
        ctx.fillStyle='#1d4ed8';ctx.fillText(label,x,y);
    };
    ctx.save();ctx.strokeStyle='#2563eb';ctx.lineWidth=1.2/z;
    ctx.beginPath();
    const ty=station.y-22/z,rx=station.x+station.w+24/z;
    ctx.moveTo(station.x,ty);ctx.lineTo(station.x+station.w,ty);
    ctx.moveTo(rx,station.y);ctx.lineTo(rx,station.y+station.h);
    for(const x of [station.x,station.x+station.w]) {ctx.moveTo(x,ty-5/z);ctx.lineTo(x,ty+5/z);}
    for(const y of [station.y,station.y+station.h]) {ctx.moveTo(rx-5/z,y);ctx.lineTo(rx+5/z,y);}
    ctx.stroke();
    labelStyle(meterLabel(station.w,pixelsPerMeter),station.x+station.w/2,ty-9/z);
    labelStyle(meterLabel(station.h,pixelsPerMeter),rx+10/z,station.y+station.h/2);
    ctx.restore();
}
export function drawStationHandles(ctx,station,zoom=1) {
    const side=9/Math.max(.05,zoom);
    ctx.save();ctx.fillStyle='#fff';ctx.strokeStyle='#1d4ed8';ctx.lineWidth=1.7/Math.max(.05,zoom);
    for(const c of STATION_CORNERS) {
        const p=stationCorner(station,c);
        ctx.fillRect(p.x-side/2,p.y-side/2,side,side);
        ctx.strokeRect(p.x-side/2,p.y-side/2,side,side);
    }
    ctx.restore();
}
