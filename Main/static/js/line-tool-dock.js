/* Dockable, collapsible Line Tool. UI state only; scenario data is unchanged. */
(() => {
  const shell = document.getElementById('builder-canvas-shell');
  const panel = document.getElementById('line-tool-panel');
  const handle = document.getElementById('line-tool-handle');
  const collapse = document.getElementById('line-tool-collapse');
  if (!shell || !panel || !handle || !collapse) return;
  const key = 'capstone-line-tool-ui';
  const allowed = new Set(['left','right','top','bottom']);
  const read = () => { try { return JSON.parse(localStorage.getItem(key) || '{}'); } catch { return {}; } };
  const restore = read();
  const setDock = (dock) => {
    if (!allowed.has(dock)) return;
    panel.dataset.dock = dock;
    panel.style.left = panel.style.top = panel.style.right = panel.style.bottom = '';
    panel.style.width = '';
  };
  const save = () => { try { localStorage.setItem(key, JSON.stringify({dock:panel.dataset.dock,collapsed:panel.classList.contains('collapsed')})); } catch {} };
  setDock(allowed.has(restore.dock) ? restore.dock : 'left');
  panel.classList.toggle('collapsed', !!restore.collapsed);
  collapse.textContent = restore.collapsed ? '+' : '−';
  collapse.setAttribute('aria-expanded', String(!restore.collapsed));
  collapse.addEventListener('click', (e) => {
    e.stopPropagation();
    const closed = panel.classList.toggle('collapsed');
    collapse.textContent = closed ? '+' : '−';
    collapse.setAttribute('aria-expanded', String(!closed));
    save();
  });
  let drag = null;
  handle.addEventListener('pointerdown', e => {
    if (e.button !== 0 || e.target.closest('button')) return;
    const rect = panel.getBoundingClientRect();
    const parent = shell.getBoundingClientRect();
    drag = {id:e.pointerId, x:e.clientX-rect.left, y:e.clientY-rect.top, startX:e.clientX, startY:e.clientY, moved:false};
    panel.style.left = `${rect.left-parent.left}px`;
    panel.style.top = `${rect.top-parent.top}px`;
    panel.style.right = panel.style.bottom = 'auto';
    panel.style.width = `${rect.width}px`;
    handle.setPointerCapture(e.pointerId);
    e.preventDefault();
  });
  handle.addEventListener('pointermove', e => {
    if (!drag || e.pointerId !== drag.id) return;
    const parent = shell.getBoundingClientRect();
    const dx=e.clientX-drag.startX,dy=e.clientY-drag.startY;
    if (Math.hypot(dx,dy)>5) drag.moved=true;
    panel.style.left = `${Math.max(0,Math.min(parent.width-panel.offsetWidth,e.clientX-parent.left-drag.x))}px`;
    panel.style.top = `${Math.max(0,Math.min(parent.height-panel.offsetHeight,e.clientY-parent.top-drag.y))}px`;
  });
  const endDrag = (e) => {
    if (!drag || e.pointerId !== drag.id) return;
    const rect = shell.getBoundingClientRect();
    // Dock by the pointer release position, not the panel center. A wide
    // horizontal toolbar otherwise cannot be moved back to either side.
    const cx=Math.max(0,Math.min(rect.width,e.clientX-rect.left));
    const cy=Math.max(0,Math.min(rect.height,e.clientY-rect.top));
    const dists = {left:cx, right:rect.width-cx, top:cy, bottom:rect.height-cy};
    const dock = Object.entries(dists).sort((a,b)=>a[1]-b[1])[0][0];
    setDock(dock); save(); drag=null;
  };
  handle.addEventListener('pointerup', endDrag);
  handle.addEventListener('pointercancel', endDrag);
})();
