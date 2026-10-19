import {drawDirection} from "./line-direction.js";
import {drawStationText} from "./canvas-tools.js";
import {operatorLegendEntries} from "./operator-highlight.js";

// ============================================================
// draw.js
// Canvas drawing functions
// ============================================================

// --------------------------------------------------------
// Convert [r, g, b] array to a valid CSS color string
// --------------------------------------------------------
function toRgbString(colorArray) {
    if (Array.isArray(colorArray)) {
        return `rgb(${colorArray[0]}, ${colorArray[1]}, ${colorArray[2]})`;
    }
    return colorArray;
}

function toRgbaString(colorArray, alpha = 1) {
    if (Array.isArray(colorArray)) {
        return `rgba(${colorArray[0]}, ${colorArray[1]}, ${colorArray[2]}, ${alpha})`;
    }
    return colorArray;
}

const COLORS = {
    white:        "#ffffff",
    black:        "#000000",
    gray:         "#c8c8c8",
    darkBlue:     "#1e3c78",
    green:        "#32b45a",
    yellow:       "#ffc800",
    activeBorder: "#ffdc00",
    boxOut:       "#dc3232",
    boxIn:        "#32b432",
};

// --------------------------------------------------------
// Draw a station rectangle
// --------------------------------------------------------
export function drawStation(ctx, sid, pos, stationInfo, isActive, activeColor) {
    const { x, y, w, h } = pos;

    if (isActive) {
        ctx.strokeStyle = COLORS.activeBorder;
        ctx.lineWidth   = 3;
        ctx.strokeRect(x - 3, y - 3, w + 6, h + 6);
        ctx.fillStyle = toRgbString(activeColor);
    } else {
        ctx.fillStyle = COLORS.gray;
    }
    ctx.fillRect(x, y, w, h);

    ctx.fillStyle    = COLORS.black;
    ctx.font         = "11px Arial";
    ctx.textAlign    = "left";
    ctx.textBaseline = "top";

    drawStationText(ctx, sid, stationInfo, pos);
}

// --------------------------------------------------------
// Draw dotted rectangle border
// --------------------------------------------------------
function drawDottedRect(ctx, color, x, y, w, h, dash = 5) {
    ctx.strokeStyle = color;
    ctx.lineWidth   = 1;
    ctx.setLineDash([dash, dash]);
    ctx.strokeRect(x, y, w, h);
    ctx.setLineDash([]);
}

// --------------------------------------------------------
// Draw a scenario box (SWIP / IN / OUT) — Phase 10
// liveState is the box's current runtime state:
//   swip -> { has_part: bool }
//   in   -> { remaining: number }
//   out  -> { count: number }
// --------------------------------------------------------
const BOX_COLORS = {
    swip: "#1e3c78",
    in:   "#32b432",
    out:  "#dc3232",
    direction: "#666666",
};

export function drawBox(ctx, bid, pos, boxData, liveState, partImage, flashTime = 0, lineDirectionImage = null) {
    const { x, y, w, h } = pos;
    const color = BOX_COLORS[boxData.type] || "#888888";

    if (boxData.type === 'direction') {
        drawDirection(ctx, boxData, lineDirectionImage);
        return;
    }

    ctx.fillStyle = COLORS.white;
    ctx.fillRect(x, y, w, h);

    drawDottedRect(ctx, color, x, y, w, h, 4);

    ctx.fillStyle    = color;
    ctx.font         = "12px Arial";
    ctx.textAlign    = "left";
    ctx.textBaseline = "top";
    ctx.fillText(boxData.name, x + 5, y + 5);

    ctx.textAlign = "center";

    if (boxData.type === "in") {
        ctx.font = "18px Arial";
        ctx.fillStyle = liveState.remaining < 5 ? BOX_COLORS.out : COLORS.black;
        ctx.fillText(liveState.remaining, x + w / 2, y + h / 2 + 6);
        ctx.font = "10px Arial";
        ctx.fillStyle = "#888888";
        ctx.fillText("remaining", x + w / 2, y + h - 12);

    } else if (boxData.type === "out") {
        ctx.font = "16px Arial";
        ctx.fillStyle = COLORS.black;
        ctx.fillText(`${liveState.count} / ${boxData.capacity}`, x + w / 2, y + h / 2 + 6);
        ctx.font = "10px Arial";
        ctx.fillStyle = "#888888";
        ctx.fillText("packed", x + w / 2, y + h - 12);
    }
    // NOTE: SWIP boxes intentionally show no separate has_part symbol here —
    // occupancy is now represented by the real part icon, drawn on top by
    // simulate.html's "dropped parts" pass.

    ctx.textAlign    = "left";
    ctx.textBaseline = "alphabetic";

    const isFull  = boxData.type === "out" && liveState.count >= boxData.capacity;
    const isEmpty = boxData.type === "in"  && liveState.remaining <= 0;

    if (isFull || isEmpty) {
        const alpha = 0.4 + 0.6 * Math.abs(Math.sin(flashTime / 200));
        ctx.strokeStyle = `rgba(220, 0, 0, ${alpha})`;
        ctx.lineWidth   = 4;
        ctx.strokeRect(x - 3, y - 3, w + 6, h + 6);
        ctx.fillStyle    = `rgba(220, 0, 0, ${alpha})`;
        ctx.font         = "10px Arial";
        ctx.textAlign    = "center";
        ctx.textBaseline = "bottom";
        ctx.fillText(isFull ? "FULL" : "EMPTY", x + w / 2, y - 6);
        ctx.textAlign    = "left";
        ctx.textBaseline = "alphabetic";
    }
}

// --------------------------------------------------------
// Draw part image at a coordinate (centered)
// --------------------------------------------------------
export function drawPart(ctx, cx, cy, partImage, size = 20) {
    if (partImage && partImage.complete && partImage.naturalWidth > 0) {
        ctx.drawImage(partImage, cx - size / 2, cy - size / 2, size, size);
    } else {
        drawPartPlaceholder(ctx, cx, cy);
    }
}

// --------------------------------------------------------
// Fallback hatched circle if part image not loaded
// --------------------------------------------------------
function drawPartPlaceholder(ctx, cx, cy, radius = 10) {
    ctx.fillStyle = COLORS.black;
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.fill();

    ctx.strokeStyle = COLORS.white;
    ctx.lineWidth = 1;
    for (let offset = -radius; offset <= radius; offset += 4) {
        ctx.beginPath();
        ctx.moveTo(cx - radius, cy + offset);
        ctx.lineTo(cx + radius, cy + offset);
        ctx.stroke();
    }

    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.stroke();
}

// --------------------------------------------------------
// Draw an operator circle with label
// --------------------------------------------------------
export function drawOperatorTracer(ctx, points, color, currentTime, maxAge = 1.25) {
    if (!Array.isArray(points) || points.length < 2) return;
    ctx.save();
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    for (let i = 1; i < points.length; i++) {
        const previous = points[i - 1];
        const point = points[i];
        const age = currentTime - point.time;
        const alpha = Math.max(0, 1 - age / maxAge) * 0.7;
        if (alpha <= 0.02) continue;
        ctx.strokeStyle = toRgbaString(color, alpha);
        ctx.lineWidth = Math.max(2, 10 * alpha);
        ctx.beginPath();
        ctx.moveTo(previous.x, previous.y);
        ctx.lineTo(point.x, point.y);
        ctx.stroke();
    }
    ctx.restore();
}

export function drawOperator(ctx, name, cx, cy, color) {
    ctx.fillStyle = toRgbaString(color);
    ctx.beginPath();
    ctx.arc(cx, cy, 14, 0, Math.PI * 2);
    ctx.fill();

    ctx.strokeStyle = COLORS.white;
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.fillStyle    = COLORS.white;
    ctx.font         = "11px Arial";
    ctx.textAlign    = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(name, cx, cy);
    ctx.textAlign    = "left";
    ctx.textBaseline = "alphabetic";
}

// --------------------------------------------------------
// Draw the top banner with clock and progress bar
// --------------------------------------------------------
export function drawBanner(ctx, simClock, taktTime, taktResetCount, width) {
    ctx.fillStyle = COLORS.darkBlue;
    ctx.fillRect(0, 0, width, 130);

    const barMaxWidth = width - 40;
    const barWidth     = Math.min(barMaxWidth, (simClock / taktTime) * barMaxWidth);

    ctx.fillStyle = COLORS.gray;
    ctx.fillRect(20, 85, barMaxWidth, 25);

    ctx.fillStyle = COLORS.green;
    ctx.fillRect(20, 85, barWidth, 25);

    ctx.strokeStyle = COLORS.white;
    ctx.lineWidth   = 2;
    ctx.strokeRect(20, 85, barMaxWidth, 25);

    ctx.fillStyle    = COLORS.white;
    ctx.font         = "24px Arial";
    ctx.textAlign    = "left";
    ctx.textBaseline = "top";
    ctx.fillText(`Cycle Time: ${simClock.toFixed(1)} / ${taktTime} min`, 20, 20);

    ctx.fillStyle = COLORS.yellow;
    ctx.font      = "16px Arial";
    ctx.fillText(`Takt Cycles Completed: ${taktResetCount}`, 20, 60);
}

// --------------------------------------------------------
// Draw legend at the bottom of the canvas
// --------------------------------------------------------
export function drawLegend(ctx, operatorNames, operators, partImage, height, highlightedOperator = null) {
    const entries = operatorLegendEntries(operatorNames, height);
    ctx.save();
    for (const entry of entries) {
        const isHighlighted = highlightedOperator === entry.id;
        if (highlightedOperator && !isHighlighted) ctx.globalAlpha = 0.22;
        else ctx.globalAlpha = 1;

        if (isHighlighted) {
            ctx.fillStyle = 'rgba(219,234,254,0.95)';
            ctx.fillRect(entry.left, entry.top + 6, entry.width - 2, 34);
            ctx.strokeStyle = '#1e3c78';
            ctx.lineWidth = 2;
            ctx.strokeRect(entry.left, entry.top + 6, entry.width - 2, 34);
        }
        ctx.fillStyle = toRgbString(operators[entry.id].color);
        ctx.beginPath();
        ctx.arc(entry.x, entry.y, 8, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = COLORS.black;
        ctx.font = '12px Arial';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        ctx.fillText(entry.id, entry.x + 12, entry.y);
    }
    ctx.globalAlpha = 1;
    const partX = entries.length ? entries[entries.length - 1].right + 28 : 20;
    drawPart(ctx, partX, height - 30, partImage);
    ctx.fillStyle = COLORS.black;
    ctx.fillText('= Part', partX + 14, height - 30);
    ctx.restore();
}
