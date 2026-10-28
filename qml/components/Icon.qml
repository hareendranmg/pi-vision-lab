import QtQuick

// Small vector glyphs (the Pi image ships no emoji font).
Canvas {
    id: icon
    property string name: ""
    property color color: "white"
    property real stroke: Math.max(2, width / 14)
    onNameChanged: requestPaint()
    onColorChanged: requestPaint()
    onWidthChanged: requestPaint()

    onPaint: {
        const g = getContext("2d")
        const w = width, h = height, s = Math.min(w, h)
        g.reset()
        g.strokeStyle = color
        g.fillStyle = color
        g.lineWidth = stroke
        g.lineCap = "round"
        g.lineJoin = "round"
        const cx = w / 2, cy = h / 2

        if (name === "objects") {
            const m = s * 0.12, L = s * 0.28
            g.beginPath()
            g.moveTo(m, m + L); g.lineTo(m, m); g.lineTo(m + L, m)
            g.moveTo(w - m - L, m); g.lineTo(w - m, m); g.lineTo(w - m, m + L)
            g.moveTo(w - m, h - m - L); g.lineTo(w - m, h - m); g.lineTo(w - m - L, h - m)
            g.moveTo(m + L, h - m); g.lineTo(m, h - m); g.lineTo(m, h - m - L)
            g.stroke()
            g.beginPath(); g.arc(cx, cy, s * 0.14, 0, Math.PI * 2); g.fill()
        } else if (name === "face") {
            g.beginPath(); g.arc(cx, cy, s * 0.4, 0, Math.PI * 2); g.stroke()
            g.beginPath(); g.arc(cx - s * 0.14, cy - s * 0.08, s * 0.05, 0, Math.PI * 2); g.fill()
            g.beginPath(); g.arc(cx + s * 0.14, cy - s * 0.08, s * 0.05, 0, Math.PI * 2); g.fill()
            g.beginPath(); g.arc(cx, cy + s * 0.02, s * 0.2, 0.15 * Math.PI, 0.85 * Math.PI); g.stroke()
        } else if (name === "color") {
            const r = s * 0.24
            const spots = [[cx, cy - r * 0.6, "#ff4d6d"], [cx - r * 0.6, cy + r * 0.45, "#3ddc97"], [cx + r * 0.6, cy + r * 0.45, "#4d9bff"]]
            g.globalAlpha = 0.8
            for (const p of spots) { g.fillStyle = p[2]; g.beginPath(); g.arc(p[0], p[1], r, 0, Math.PI * 2); g.fill() }
            g.globalAlpha = 1
        } else if (name === "back") {
            g.beginPath(); g.moveTo(w * 0.62, h * 0.2); g.lineTo(w * 0.3, h * 0.5); g.lineTo(w * 0.62, h * 0.8); g.stroke()
        } else if (name === "hand") {
            // Palm with four fingers and a thumb.
            g.beginPath()
            g.moveTo(w * 0.3, h * 0.9); g.lineTo(w * 0.72, h * 0.9)
            g.moveTo(w * 0.3, h * 0.9); g.lineTo(w * 0.24, h * 0.5)
            g.moveTo(w * 0.72, h * 0.9); g.lineTo(w * 0.8, h * 0.55)
            for (let i = 0; i < 4; i++) {
                const x = w * (0.32 + i * 0.13)
                g.moveTo(x, h * 0.55); g.lineTo(x, h * (i === 0 || i === 3 ? 0.22 : 0.1))
            }
            g.moveTo(w * 0.24, h * 0.55); g.lineTo(w * 0.1, h * 0.38)
            g.stroke()
        }
    }
}
