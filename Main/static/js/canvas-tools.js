// Shared canvas view controls. The view never changes saved layout coordinates.
export class CanvasViewport {
    constructor(canvas, controls, onChange = () => {}) {
        this.canvas = canvas;
        this.scale = 1;
        this.x = 0;
        this.y = 0;
        this.isPanning = false;
        this.onChange = onChange;
        this.label = controls.querySelector('[data-zoom-label]');
        controls.querySelector('[data-zoom-in]').onclick = () => this.zoom(1.25);
        controls.querySelector('[data-zoom-out]').onclick = () => this.zoom(0.8);
        controls.querySelector('[data-zoom-reset]').onclick = () => this.reset();
        canvas.addEventListener('wheel', e => {
            e.preventDefault();
            this.zoom(Math.exp(-Math.max(-100, Math.min(100, e.deltaY)) * 0.002), this.pixelPoint(e));
        }, { passive: false });
        canvas.addEventListener('mousedown', e => {
            if (e.button !== 1 && !(e.button === 0 && e.shiftKey)) return;
            e.preventDefault();
            this.isPanning = true;
            this.panStart = this.pixelPoint(e);
            this.panOrigin = { x: this.x, y: this.y };
            canvas.style.cursor = 'grabbing';
        }, true);
        window.addEventListener('mousemove', e => {
            if (!this.isPanning) return;
            const p = this.pixelPoint(e);
            this.x = this.panOrigin.x + p.x - this.panStart.x;
            this.y = this.panOrigin.y + p.y - this.panStart.y;
            this.changed();
        });
        window.addEventListener('mouseup', () => {
            if (!this.isPanning) return;
            this.isPanning = false;
            this.suppressClick = true;
            canvas.style.cursor = 'default';
            setTimeout(() => { this.suppressClick = false; }, 0);
        });
        canvas.addEventListener('click', e => {
            if (this.suppressClick || e.shiftKey) { e.stopImmediatePropagation(); e.preventDefault(); }
        }, true);
        this.changed(false);
    }
    pixelPoint(e) {
        const r = this.canvas.getBoundingClientRect();
        return { x: (e.clientX - r.left) * this.canvas.width / r.width,
                 y: (e.clientY - r.top) * this.canvas.height / r.height };
    }
    worldPoint(e) {
        const p = this.pixelPoint(e);
        return { x: (p.x - this.x) / this.scale, y: (p.y - this.y) / this.scale };
    }
    zoom(factor, p = { x: this.canvas.width / 2, y: this.canvas.height / 2 }) {
        const next = Math.max(0.25, Math.min(8, this.scale * factor));
        this.x = p.x - (p.x - this.x) * next / this.scale;
        this.y = p.y - (p.y - this.y) * next / this.scale;
        this.scale = next;
        this.changed();
    }
    reset() { this.scale = 1; this.x = this.y = 0; this.changed(); }
    apply(ctx) { ctx.translate(this.x, this.y); ctx.scale(this.scale, this.scale); }
    changed(redraw = true) {
        if (this.label) this.label.textContent = Math.round(this.scale * 100) + '%';
        if (redraw) this.onChange();
    }
}

// Wrap by measured width, including names with no spaces. Preserve every character.
export function wrapCanvasText(ctx, text, maxWidth) {
    const lines = [];
    for (const paragraph of String(text ?? '').split('\n')) {
        let line = '';
        for (const char of paragraph) {
            const candidate = line + char;
            if (line && ctx.measureText(candidate).width > maxWidth) {
                const split = line.lastIndexOf(' ');
                if (split > 0) {
                    lines.push(line.slice(0, split));
                    line = line.slice(split + 1) + char;
                } else { lines.push(line); line = char; }
            } else { line = candidate; }
        }
        lines.push(line.trimEnd());
    }
    return lines;
}

export function stationProcesses(s) {
    return s.processes || [{id: 'p1', name: 'Process 1', manual_time: s.cycle_time ?? 10, auto_time: 0}];
}
export function stationTotals(s) {
    return stationProcesses(s).reduce((total, p) => ({manual: total.manual + Number(p.manual_time || 0), auto: total.auto + Number(p.auto_time || 0)}), {manual: 0, auto: 0});
}
export function drawStationText(ctx, sid, s, pos = s) {
    ctx.save();
    ctx.fillStyle = '#000000';
    ctx.font = '11px Arial';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.beginPath();
    ctx.rect(pos.x + 2, pos.y + 2, pos.w - 4, pos.h - 4);
    ctx.clip();
    ctx.fillText(`S${sid}`, pos.x + 4, pos.y + 4);
    const lines = wrapCanvasText(ctx, s.name, Math.max(1, pos.w - 8));
    const count = Math.max(1, Math.floor((pos.h - 50) / 13));
    lines.slice(0, count).forEach((line, i) => {
        if (i === count - 1 && lines.length > count) {
            while (line && ctx.measureText(line + '…').width > pos.w - 8) line = line.slice(0, -1);
            line += '…';
        }
        ctx.fillText(line, pos.x + 4, pos.y + 20 + i * 13);
    });
    const totals = stationTotals(s);
    ctx.font = '10px Arial';
    ctx.fillText(`M:${Number(totals.manual.toFixed(2))} A:${Number(totals.auto.toFixed(2))} min`, pos.x + 4, pos.y + pos.h - 28);
    ctx.fillText(`No. of processes: ${stationProcesses(s).length}`, pos.x + 4, pos.y + pos.h - 15);
    ctx.restore();
}

export function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
}
