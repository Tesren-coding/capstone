// Layout-only alignment and measurements. All coordinates are unzoomed canvas
// units; tolerance and line thickness are converted from screen pixels.
import {STATION_GAP} from './builder-snapping.js';

const SCREEN_SNAP_PX = 10;
const PERPENDICULAR_RANGE = 110;
const MEASURE_RANGE = 600;

export function metersFromCanvas(units, pixelsPerMeter = 50) {
    const scale = Number(pixelsPerMeter);
    return Math.abs(units) / (Number.isFinite(scale) && scale > 0 ? scale : 50);
}
export function meterLabel(units, pixelsPerMeter = 50) {
    return `${metersFromCanvas(units, pixelsPerMeter).toFixed(2)} m`;
}

const mid = (a,b) => (a+b)/2;
const overlap = (a,b,c,d) => Math.min(b,d) - Math.max(a,c);
const anchors = (rect,axis) => axis==='x'
    ? [{at:rect.x,kind:'left'}, {at:rect.x+rect.w/2,kind:'center'}, {at:rect.x+rect.w,kind:'right'}]
    : [{at:rect.y,kind:'top'}, {at:rect.y+rect.h/2,kind:'center'}, {at:rect.y+rect.h,kind:'bottom'}];
const otherAxisNearby = (a,b,axis) => axis==='x'
    ? overlap(a.y,a.y+a.h,b.y,b.y+b.h)>=-PERPENDICULAR_RANGE
    : overlap(a.x,a.x+a.w,b.x,b.x+b.w)>=-PERPENDICULAR_RANGE;

function snapAxis(rect,targets,axis,tolerance,{dockStations=false}={}) {
    const a=anchors(rect,axis);
    let best=null;
    for(const target of targets) {
        const b=target.rect;
        if (!otherAxisNearby(rect,b,axis)) continue;
        for(const targetAnchor of anchors(b,axis)) {
            for(const movingAnchor of a) {
                const diff=targetAnchor.at-movingAnchor.at;
                const abs=Math.abs(diff);
                if(abs>tolerance) continue;
                // Match like-for-like edges and centers first when equally close.
                const priority=targetAnchor.kind===movingAnchor.kind ? 0 : 1;
                if(!best || abs<best.abs-0.01 || (Math.abs(abs-best.abs)<0.01 && priority<best.priority)) {
                    best={delta:diff,abs,priority, at:targetAnchor.at,
                        kind:movingAnchor.kind==='center'&&targetAnchor.kind==='center'?'center':'edge',
                        target:b, axis};
                }
            }
        }
        // Preserve the familiar small clearance between adjacent stations.
        // A station gap never applies when aligning with material boxes/arrows.
        if(dockStations && target.type==='station') {
            const endpoints=axis==='x'
                ? [{from:rect.x,to:b.x+b.w+STATION_GAP},
                   {from:rect.x+rect.w,to:b.x-STATION_GAP}]
                : [{from:rect.y,to:b.y+b.h+STATION_GAP},
                   {from:rect.y+rect.h,to:b.y-STATION_GAP}];
            for(const endpoint of endpoints) {
                const diff=endpoint.to-endpoint.from,abs=Math.abs(diff);
                if(abs<=tolerance && (!best || abs<best.abs-0.01)) {
                    best={delta:diff,abs,priority:2,at:endpoint.to,kind:'gap',target:b,axis};
                }
            }
        }
    }
    return best;
}

// Measurements describe *true edge-to-edge gaps*, not distances between centers.
// Only objects overlapping on the perpendicular axis are considered.
export function nearestGapMeasurements(rect, targets, maxRange=MEASURE_RANGE) {
    let nearestX=null, nearestY=null;
    for(const target of targets) {
        const b=target.rect;
        const sharedY=overlap(rect.y,rect.y+rect.h,b.y,b.y+b.h);
        const sharedX=overlap(rect.x,rect.x+rect.w,b.x,b.x+b.w);
        if(sharedY>=0) {
            const y=mid(Math.max(rect.y,b.y),Math.min(rect.y+rect.h,b.y+b.h));
            let from,to;
            if(rect.x>=b.x+b.w) {from=b.x+b.w;to=rect.x;}
            else if(b.x>=rect.x+rect.w) {from=rect.x+rect.w;to=b.x;}
            if(from!==undefined && to-from<=maxRange && (!nearestX || to-from<nearestX.distance))
                nearestX={axis:'x',from,to,cross:y,distance:to-from};
        }
        if(sharedX>=0) {
            const x=mid(Math.max(rect.x,b.x),Math.min(rect.x+rect.w,b.x+b.w));
            let from,to;
            if(rect.y>=b.y+b.h) {from=b.y+b.h;to=rect.y;}
            else if(b.y>=rect.y+rect.h) {from=rect.y+rect.h;to=b.y;}
            if(from!==undefined && to-from<=maxRange && (!nearestY || to-from<nearestY.distance))
                nearestY={axis:'y',from,to,cross:x,distance:to-from};
        }
    }
    return [nearestX,nearestY].filter(Boolean);
}

// Targets: [{type:'station'|'box', id, rect:{x,y,w,h}}].
// Snapping never modifies saved data; the caller applies the resulting x/y.
export function smartSnapRect(rect,targets,zoom=1,{dockStations=false,snap=true}={}) {
    const tolerance=SCREEN_SNAP_PX/Math.max(0.05,Number(zoom)||1);
    const sx=snap ? snapAxis(rect,targets,'x',tolerance,{dockStations}) : null;
    const sy=snap ? snapAxis(rect,targets,'y',tolerance,{dockStations}) : null;
    const snapped={...rect,x:rect.x+(sx?.delta||0),y:rect.y+(sy?.delta||0)};
    return {x:snapped.x,y:snapped.y,
        guides:[sx,sy].filter(Boolean).map(g=>({axis:g.axis,at:g.at,kind:g.kind,target:g.target})),
        measurements:nearestGapMeasurements(snapped,targets),rect:snapped};
}

export function drawSmartGuides(ctx, data, pixelsPerMeter=50, zoom=1) {
    if(!data) return;
    const z=Math.max(0.05,zoom);
    ctx.save();
    ctx.font=`${11/z}px Arial`;
    ctx.textAlign='center';ctx.textBaseline='middle';
    for(const guide of data.guides || []) {
        const a=data.rect,b=guide.target;
        ctx.beginPath();ctx.strokeStyle='#d83f89';ctx.lineWidth=1.35/z;
        ctx.setLineDash([5/z,4/z]);
        if(guide.axis==='x') {
            const min=Math.min(a.y,b.y)-28/z,max=Math.max(a.y+a.h,b.y+b.h)+28/z;
            ctx.moveTo(guide.at,min);ctx.lineTo(guide.at,max);
        } else {
            const min=Math.min(a.x,b.x)-28/z,max=Math.max(a.x+a.w,b.x+b.w)+28/z;
            ctx.moveTo(min,guide.at);ctx.lineTo(max,guide.at);
        }
        ctx.stroke();ctx.setLineDash([]);
        const label=guide.kind==='center'?'Center':guide.kind==='gap'?'Gap':'Edge';
        const lx=guide.axis==='x'?guide.at:(a.x+a.w/2);
        const ly=guide.axis==='x'?Math.min(a.y,b.y)-36/z:guide.at-10/z;
        drawLabel(ctx,label,lx,ly,z,'#9a215e');
    }
    for(const m of data.measurements || []) {
        // Distance annotations are legible at every zoom level.
        const cross=m.cross;
        ctx.strokeStyle='#2563eb';ctx.lineWidth=1.3/z;
        ctx.beginPath();
        if(m.axis==='x') {
            ctx.moveTo(m.from,cross);ctx.lineTo(m.to,cross);
            ctx.moveTo(m.from,cross-5/z);ctx.lineTo(m.from,cross+5/z);
            ctx.moveTo(m.to,cross-5/z);ctx.lineTo(m.to,cross+5/z);
        } else {
            ctx.moveTo(cross,m.from);ctx.lineTo(cross,m.to);
            ctx.moveTo(cross-5/z,m.from);ctx.lineTo(cross+5/z,m.from);
            ctx.moveTo(cross-5/z,m.to);ctx.lineTo(cross+5/z,m.to);
        }
        ctx.stroke();
        const lx=m.axis==='x'?mid(m.from,m.to):cross+16/z;
        const ly=m.axis==='x'?cross-12/z:mid(m.from,m.to);
        drawLabel(ctx,meterLabel(m.distance,pixelsPerMeter),lx,ly,z,'#184fb4');
    }
    ctx.restore();
}
function drawLabel(ctx,label,x,y,z,color) {
    const w=ctx.measureText(label).width+10/z,h=17/z;
    ctx.fillStyle='rgba(255,255,255,0.96)';
    ctx.fillRect(x-w/2,y-h/2,w,h);
    ctx.strokeStyle='#d4d9e3';ctx.lineWidth=0.7/z;
    ctx.strokeRect(x-w/2,y-h/2,w,h);
    ctx.fillStyle=color;ctx.fillText(label,x,y+0.4/z);
}
