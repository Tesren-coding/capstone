// ============================================================
// layout.js
// Calculates positions of stations and special boxes
// JavaScript equivalent of layout.py
// ============================================================

// --------------------------------------------------------
// Row sequences — must match layout.py exactly
// --------------------------------------------------------
const BOTTOM_SEQUENCE = [
    ["box",     "Incoming"],
    ["station", 1],
    ["station", 2],
    ["station", 3],
    ["box",     "HT_Out"],
    ["box",     "HT_In"],
    ["station", 4],
    ["box",     "SWIP_1"],
    ["station", 5],
    ["box",     "SWIP_2"],
    ["station", 6],
    ["box",     "SWIP_3"],
    ["station", 7],
    ["station", 8],
    ["station", 9],
];

const TOP_SEQUENCE = [
    ["box",     "Packing"],
    ["station", 16],
    ["station", 15],
    ["station", 14],
    ["box",     "SWIP_7"],
    ["station", 13],
    ["box",     "SWIP_6"],
    ["box",     "Coating_Out"],
    ["station", 12],
    ["station", 11],
    ["box",     "SWIP_5"],
    ["box",     "Coating_In"],
    ["station", 10],
    ["box",     "SWIP_4"],
];

// --------------------------------------------------------
// Build all positions and centers
// dims comes from the /layout-data API response
// --------------------------------------------------------
function buildPositions(dims) {
    const stationPositions = {};
    const boxPositions     = {};

    BOTTOM_SEQUENCE.forEach((item, i) => {
        const [type, id] = item;
        const x = dims.row_start_x + i * dims.row_gap;
        if (type === "station") {
            stationPositions[id] = {
                x: x, y: dims.bottom_row_y,
                w: dims.station_width, h: dims.station_height
            };
        } else {
            boxPositions[id] = {
                x: x, y: dims.bottom_row_y,
                w: dims.box_width, h: dims.box_height
            };
        }
    });

    TOP_SEQUENCE.forEach((item, i) => {
        const [type, id] = item;
        const x = dims.row_start_x + i * dims.row_gap;
        if (type === "station") {
            stationPositions[id] = {
                x: x, y: dims.top_row_y,
                w: dims.station_width, h: dims.station_height
            };
        } else {
            boxPositions[id] = {
                x: x, y: dims.top_row_y,
                w: dims.box_width, h: dims.box_height
            };
        }
    });

    const stationCenters = {};
    for (const sid in stationPositions) {
        const p = stationPositions[sid];
        stationCenters[sid] = {
            x: p.x + p.w / 2,
            y: p.y + p.h / 2
        };
    }

    const boxCenters = {};
    for (const key in boxPositions) {
        const p = boxPositions[key];
        boxCenters[key] = {
            x: p.x + p.w / 2,
            y: p.y + p.h / 2
        };
    }

    return { stationPositions, boxPositions, stationCenters, boxCenters };
}