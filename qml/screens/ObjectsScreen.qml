import QtQuick
import "../components"

Item {
    id: screen
    readonly property real u: win.u
    readonly property var objects: backend.vision.objects || []
    readonly property real panelW: 240 * u
    readonly property var boxColors: ["#39e1ff", "#ff5fd2", "#ffd24d", "#7cff9b", "#ff8a65", "#b388ff"]

    function colorFor(label) {
        let h = 0
        for (let i = 0; i < label.length; i++) h = (h * 31 + label.charCodeAt(i)) >>> 0
        return boxColors[h % boxColors.length]
    }

    Repeater {
        model: screen.objects
        delegate: Item {
            required property var modelData
            readonly property color c: screen.colorFor(modelData.label)
            x: modelData.x * screen.width
            y: modelData.y * screen.height
            width: modelData.w * screen.width
            height: modelData.h * screen.height

            Rectangle {
                anchors.fill: parent
                color: area.containsMouse ? Qt.rgba(parent.c.r, parent.c.g, parent.c.b, 0.18) : "transparent"
                border.width: (area.containsMouse ? 4 : 2.5) * screen.u
                border.color: parent.c
                radius: 8 * screen.u
            }
            Rectangle {
                y: Math.max(-height - 4 * screen.u, -parent.y + 66 * screen.u)
                x: 0
                width: tag.implicitWidth + 16 * screen.u
                height: 26 * screen.u
                radius: 8 * screen.u
                color: parent.c
                Text {
                    id: tag
                    anchors.centerIn: parent
                    text: modelData.label + "  " + Math.round(modelData.score * 100) + "%"
                    color: "#0b0e17"
                    font.pixelSize: 14 * screen.u
                    font.bold: true
                }
            }
            MouseArea {  // highlight the box under the air cursor
                id: area
                anchors.fill: parent
                hoverEnabled: true
            }
        }
    }

    TopBar { width: parent.width; title: "Object Finder"; accent: "#39e1ff" }

    GlassPanel {
        id: panel
        anchors.left: parent.left; anchors.leftMargin: 12 * screen.u
        anchors.top: parent.top; anchors.topMargin: 70 * screen.u
        width: screen.panelW
        height: list.implicitHeight + 56 * screen.u
        Text {
            x: 16 * screen.u; y: 12 * screen.u
            text: "I can see"
            color: "#8fe9ff"; font.pixelSize: 15 * screen.u; font.bold: true
        }
        Column {
            id: list
            x: 16 * screen.u; y: 40 * screen.u
            width: parent.width - 32 * screen.u
            spacing: 6 * screen.u
            readonly property var counts: {
                const c = {}
                for (const o of screen.objects) c[o.label] = (c[o.label] || 0) + 1
                return Object.keys(c).sort((a, b) => c[b] - c[a]).map(k => ({ label: k, n: c[k] }))
            }
            Text {
                visible: list.counts.length === 0
                width: parent.width
                text: "Nothing yet. Show me a cup, phone, bottle, book, or yourself!"
                color: "#a9b3c9"; font.pixelSize: 14 * screen.u; wrapMode: Text.WordWrap
            }
            Repeater {
                model: list.counts
                delegate: Row {
                    required property var modelData
                    spacing: 10 * screen.u
                    Rectangle {
                        width: 12 * screen.u; height: width; radius: width / 2
                        color: screen.colorFor(modelData.label)
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        text: (modelData.n > 1 ? modelData.n + " × " : "") + modelData.label
                        color: "white"; font.pixelSize: 17 * screen.u; font.bold: true
                    }
                }
            }
        }
    }
}
