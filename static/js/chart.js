/**
 * LogGuard - 24-Hour DOT Grid Canvas Visualizer
 * Accurately renders the official FMCSA 4-tier stepped graph:
 *   Line 1: OFF (Off Duty)
 *   Line 2: SB  (Sleeper Berth)
 *   Line 3: D   (Driving)
 *   Line 4: ON  (On Duty Not Driving)
 */

document.addEventListener("DOMContentLoaded", () => {
    const canvas = document.getElementById("dotLogCanvas");
    if (!canvas || typeof LOG_EVENTS === "undefined") return;

    const ctx = canvas.getContext("2d");

    // Dynamic resolution scaling for crisp rendering on high-DPI displays
    const dpr = window.devicePixelRatio || 1;
    const displayWidth = canvas.clientWidth || 1000;
    const displayHeight = 260;

    canvas.width = displayWidth * dpr;
    canvas.height = displayHeight * dpr;
    ctx.scale(dpr, dpr);

    // Layout configuration
    const padding = { left: 90, right: 30, top: 40, bottom: 40 };
    const gridWidth = displayWidth - padding.left - padding.right;
    const gridHeight = displayHeight - padding.top - padding.bottom;

    const tiers = [
        { label: "1. OFF", status: "OFF", color: "#64748b" },
        { label: "2. SB",  status: "SB",  color: "#818cf8" },
        { label: "3. D",   status: "D",   color: "#38bdf8" },
        { label: "4. ON",  status: "ON",  color: "#fbbf24" }
    ];

    const rowHeight = gridHeight / 3;

    function getYForStatus(status) {
        switch (status.toUpperCase()) {
            case "OFF": return padding.top + 0 * rowHeight;
            case "SB":  return padding.top + 1 * rowHeight;
            case "D":   return padding.top + 2 * rowHeight;
            case "ON":  return padding.top + 3 * rowHeight;
            default:    return padding.top + 0 * rowHeight;
        }
    }

    function getXForTime(dateStr) {
        // Expecting date string: "YYYY-MM-DD HH:MM:SS" or ISO
        const parts = dateStr.split(" ")[1] ? dateStr.split(" ")[1].split(":") : dateStr.split("T")[1].split(":");
        const hours = parseInt(parts[0], 10);
        const mins = parseInt(parts[1], 10);
        const secs = parts[2] ? parseInt(parts[2], 10) : 0;

        const totalSecs = hours * 3600 + mins * 60 + secs;
        const fraction = totalSecs / 86400; // 86400 seconds in 24 hours
        return padding.left + fraction * gridWidth;
    }

    // Clear Canvas
    ctx.fillStyle = "#070c18";
    ctx.fillRect(0, 0, displayWidth, displayHeight);

    // 1. Draw Grid Lines (Horizontal Tier Tracks)
    tiers.forEach((tier, index) => {
        const y = padding.top + index * rowHeight;

        // Label
        ctx.fillStyle = "#94a3b8";
        ctx.font = "600 12px Inter, sans-serif";
        ctx.textAlign = "right";
        ctx.fillText(tier.label, padding.left - 15, y + 4);

        // Track Line
        ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(padding.left + gridWidth, y);
        ctx.stroke();
    });

    // 2. Draw 24-Hour Vertical Markers & 15-Minute Subticks
    for (let h = 0; h <= 24; h++) {
        const x = padding.left + (h / 24) * gridWidth;

        // Hour Grid Line
        ctx.strokeStyle = (h === 0 || h === 12 || h === 24) ? "rgba(255, 255, 255, 0.22)" : "rgba(255, 255, 255, 0.08)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(x, padding.top - 8);
        ctx.lineTo(x, padding.top + gridHeight + 8);
        ctx.stroke();

        // Hour Label (Every 2 hours or midnight/noon)
        if (h % 2 === 0) {
            ctx.fillStyle = "#64748b";
            ctx.font = "500 10px Inter, sans-serif";
            ctx.textAlign = "center";
            let label = h === 0 ? "Midnight" : (h === 12 ? "Noon" : (h > 12 ? (h - 12) + " PM" : h + " AM"));
            if (h === 24) label = "24:00";
            ctx.fillText(label, x, padding.top - 16);
        }

        // 15-minute sub-ticks along the tracks
        if (h < 24) {
            for (let q = 1; q <= 3; q++) {
                const subX = x + (q / 4) * (gridWidth / 24);
                ctx.strokeStyle = "rgba(255, 255, 255, 0.035)";
                ctx.beginPath();
                ctx.moveTo(subX, padding.top);
                ctx.lineTo(subX, padding.top + gridHeight);
                ctx.stroke();
            }
        }
    }

    // 3. Draw Duty Stepped Graph
    if (!LOG_EVENTS || LOG_EVENTS.length === 0) return;

    // Draw Shaded Driving Zones
    LOG_EVENTS.forEach(ev => {
        if (ev.status === "D") {
            const x1 = getXForTime(ev.start);
            const x2 = getXForTime(ev.end);
            ctx.fillStyle = "rgba(56, 189, 248, 0.12)";
            ctx.fillRect(x1, padding.top, Math.max(2, x2 - x1), gridHeight);
        }
    });

    // Draw Stepped Status Line
    ctx.lineWidth = 3.5;
    ctx.lineCap = "round";
    ctx.lineJoin = "miter";

    for (let i = 0; i < LOG_EVENTS.length; i++) {
        const ev = LOG_EVENTS[i];
        const xStart = getXForTime(ev.start);
        const xEnd = getXForTime(ev.end);
        const y = getYForStatus(ev.status);

        // Status Line Segment
        ctx.strokeStyle = ev.status === "D" ? "#38bdf8" : (ev.status === "ON" ? "#fbbf24" : (ev.status === "SB" ? "#818cf8" : "#94a3b8"));
        ctx.beginPath();
        ctx.moveTo(xStart, y);
        ctx.lineTo(xEnd, y);
        ctx.stroke();

        // Status Transition Step to Next Interval
        if (i < LOG_EVENTS.length - 1) {
            const nextEv = LOG_EVENTS[i + 1];
            const nextY = getYForStatus(nextEv.status);
            ctx.strokeStyle = "rgba(255, 255, 255, 0.4)";
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(xEnd, y);
            ctx.lineTo(xEnd, nextY);
            ctx.stroke();
            ctx.lineWidth = 3.5; // restore
        }

        // Draw Start Node Dot
        ctx.fillStyle = ctx.strokeStyle;
        ctx.beginPath();
        ctx.arc(xStart, y, 4, 0, Math.PI * 2);
        ctx.fill();
    }
});
