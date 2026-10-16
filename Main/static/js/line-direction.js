// Drawable, transformable line-direction marker shared by builder and playback.
// x/y are the marker's unrotated top-left corner; rotation is in degrees.
// Legacy markers with no transform fields render exactly as before.
export const DIRECTION_MIN_WIDTH = 60;
export const DIRECTION_MIN_HEIGHT = 12;

export function directionAngle(box) {
    const number = Number(box.rotation ?? 0);
    return Number.isFinite(number) ? number * Math.PI / 180 : 0;
}

export function directionCenter(box) {
    return {x: box.x + box.w / 2, y: box.y + box.h / 2};
}

export function directionLocalPoint(box, x, y) {
    const center = directionCenter(box);
    const angle = directionAngle(box);
    const dx = x - center.x, dy = y - center.y;
    return {x: dx * Math.cos(angle) + dy * Math.sin(angle),
            y: -dx * Math.sin(angle) + dy * Math.cos(angle)};
}

export function directionContainsPoint(box, x, y, padding = 0) {
    const local = directionLocalPoint(box, x, y);
    return Math.abs(local.x) <= box.w / 2 + padding &&
        Math.abs(local.y) <= box.h / 2 + padding;
}

export function directionResizeHandle(box) {
    const center = directionCenter(box);
    const angle = directionAngle(box);
    return {x: center.x + box.w / 2 * Math.cos(angle) - box.h / 2 * Math.sin(angle),
            y: center.y + box.w / 2 * Math.sin(angle) + box.h / 2 * Math.cos(angle)};
}

export function resizeDirectionFromPoint(box, x, y) {
    // Resize about the existing centre. The handle always corresponds to the
    // unflipped bottom-right corner, even if the PNG is mirrored.
    const center = directionCenter(box);
    const point = directionLocalPoint(box, x, y);
    box.w = Math.round(Math.max(DIRECTION_MIN_WIDTH, 2 * point.x));
    box.h = Math.round(Math.max(DIRECTION_MIN_HEIGHT, 2 * point.y));
    box.x = center.x - box.w / 2;
    box.y = center.y - box.h / 2;
}

export function drawDirection(ctx, box, image, {selected = false, viewScale = 1} = {}) {
    const center = directionCenter(box);
    ctx.save();
    ctx.translate(center.x, center.y);
    ctx.rotate(directionAngle(box));
    ctx.save();
    ctx.scale(box.flip_horizontal ? -1 : 1, box.flip_vertical ? -1 : 1);
    if (image?.complete && image.naturalWidth > 0) {
        ctx.drawImage(image, -box.w / 2, -box.h / 2, box.w, box.h);
    } else {
        // The marker remains recognizable while the PNG loads.
        ctx.strokeStyle = '#555';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(-box.w / 2 + 8, 0);
        ctx.lineTo(box.w / 2 - 16, 0);
        ctx.moveTo(box.w / 2 - 30, -Math.min(10, box.h / 3));
        ctx.lineTo(box.w / 2 - 16, 0);
        ctx.lineTo(box.w / 2 - 30, Math.min(10, box.h / 3));
        ctx.stroke();
    }
    ctx.restore();
    if (selected) {
        ctx.strokeStyle = '#0066ff';
        ctx.lineWidth = 2 / viewScale;
        ctx.setLineDash([5 / viewScale, 4 / viewScale]);
        ctx.strokeRect(-box.w / 2, -box.h / 2, box.w, box.h);
        ctx.setLineDash([]);
        // Resize handle is always at the bottom-right of the unflipped frame.
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(box.w / 2 - 5 / viewScale, box.h / 2 - 5 / viewScale,
            10 / viewScale, 10 / viewScale);
        ctx.strokeStyle = '#0066ff';
        ctx.strokeRect(box.w / 2 - 5 / viewScale, box.h / 2 - 5 / viewScale,
            10 / viewScale, 10 / viewScale);
    }
    ctx.restore();
    // Keep text legible when the graphic is rotated or mirrored.
    const angle = directionAngle(box);
    const topExtent = (Math.abs(Math.sin(angle)) * box.w + Math.abs(Math.cos(angle)) * box.h) / 2;
    ctx.save();
    ctx.fillStyle = '#333333';
    ctx.font = '11px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'bottom';
    ctx.fillText(box.name || 'Line Direction', center.x, center.y - topExtent - 5);
    ctx.restore();
}
