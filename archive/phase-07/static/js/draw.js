// ============================================================
// draw.js
// Canvas drawing functions
// JavaScript equivalent of drawing.py
// ============================================================

// --------------------------------------------------------
// Convert [r, g, b] array to a valid CSS color string
// --------------------------------------------------------
function toRgbString(colorArray) {
    if (Array.isArray(colorArray)) {
        return `rgb(${colorArray[0]}, ${colorArray[1]}, ${colorArray[2]})`;
    }
    return colorArray; // already a string, return as-is
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

const BOX_TYPES = {
    "Incoming":    "in",
    "HT_Out":      "out",
    "HT_In":       "in",
    "Coating_In":  "in",
    "Coating_Out": "out",
    "Packing":     "out",
    "SWIP_1":      "out",
    "SWIP_2":      "out",
    "SWIP_3":      "out",
    "SWIP_4":      "out",
    "SWIP_5":      "out",
    "SWIP_6":      "out",
    "SWIP_7":      "out",
};

// --------------------------------------------------------
// Draw a station rectangle
// --------------------------------------------------------
function drawStation(ctx, sid, pos, stationInfo, isActive, activeColor) {
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
    ctx.fillText(`S${sid}`, x + 4, y + 4);

    // wrap station name onto two lines
    const words = stationInfo.name.split(" ");
    const mid   = Math.ceil(words.length / 2);
    const line1 = words.slice(0, mid).join(" ");
    const line2 = words.slice(mid).join(" ");
    ctx.fillText(line1, x + 4, y + 22);
    ctx.fillText(line2, x + 4, y + 38);

    ctx.fillText(`CT: ${stationInfo.cycle_time}m`, x + 4, y + 56);
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
// Draw a special box (Incoming, Packing, HT, Coating, SWIP)
// --------------------------------------------------------
function drawBox(ctx, key, pos, boxInfo, counters, images, partImage) {
    const { x, y, w, h } = pos;
    const boxType  = BOX_TYPES[key] || "in";
    const dotColor = boxType === "out" ? COLORS.boxOut : COLORS.boxIn;

    const img = images[key];
    if (img && img.complete && img.naturalWidth > 0) {
        ctx.drawImage(img, x, y, w, h);
    } else {
        ctx.fillStyle = COLORS.white;
        ctx.fillRect(x, y, w, h);
    }

    // image only boxes (SWIP) — already have their own border baked
    // into the image, so skip the dotted overlay and label entirely
    if (boxInfo.type === "image") {
        return;
    }

    drawDottedRect(ctx, dotColor, x, y, w, h);

    ctx.fillStyle    = dotColor;
    ctx.font         = "12px Arial";
    ctx.textAlign    = "left";
    ctx.textBaseline = "top";
    ctx.fillText(boxInfo.label, x + 5, y + 8);

    if (boxInfo.type === "counter") {
        const count = key === "Incoming" ? counters.incoming : counters.packing;

        ctx.fillStyle = (key === "Incoming" && count < 10) ? COLORS.boxOut : COLORS.black;
        ctx.font      = "26px Arial";
        ctx.textAlign = "center";
        ctx.fillText(count, x + w / 2, y + 25);

        ctx.textAlign = "left";
        ctx.fillStyle = "#888888";
        ctx.font      = "11px Arial";
        ctx.fillText(key === "Incoming" ? "remaining" : "packed", x + 3, y + h - 18);
    } else if (!(img && img.complete && img.naturalWidth > 0)) {
    // buffer box with no image — draw the actual part image
    drawPart(ctx, x + w / 2, y + h - 20, partImage);
    }
}

// --------------------------------------------------------
// Draw part image at a coordinate (centered)
// --------------------------------------------------------
function drawPart(ctx, cx, cy, partImage, size = 20) {
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
function drawOperator(ctx, name, cx, cy, color) {
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
// Convert [r, g, b] array to a semi-transparent CSS color
// --------------------------------------------------------
function toRgbaString(colorArray, alpha = 1) {
    if (Array.isArray(colorArray)) {
        return `rgba(${colorArray[0]}, ${colorArray[1]}, ${colorArray[2]}, ${alpha})`;
    }
    return colorArray;
}
// --------------------------------------------------------
// Draw the top banner with clock and progress bar
// --------------------------------------------------------
function drawBanner(ctx, simClock, taktTime, taktResetCount, width) {
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
function drawLegend(ctx, operatorNames, operators, partImage, height) {
    let legendX = 20;
    const legendY = height - 30;

    operatorNames.forEach(op => {
        ctx.fillStyle = toRgbString(operators[op].color);
        ctx.beginPath();
        ctx.arc(legendX, legendY, 8, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle    = COLORS.black;
        ctx.font         = "12px Arial";
        ctx.textBaseline = "middle";
        ctx.fillText(op, legendX + 12, legendY);

        legendX += 80;
    });

    drawPart(ctx, legendX, legendY, partImage);
    ctx.fillStyle = COLORS.black;
    ctx.fillText("= Part", legendX + 14, legendY);
}