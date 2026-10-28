import QtQuick
import "../components"

Item {
    id: screen
    readonly property real u: win.u
    readonly property var c: backend.vision.color || { r: 0, g: 0, b: 0, hex: "#000000", name: "..." }
    readonly property color current: c.hex

    // Tint the screen with the detected colour.
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: "transparent" }
            GradientStop { position: 1; color: Qt.rgba(screen.current.r, screen.current.g, screen.current.b, 0.55) }
        }
    }

    // Sampling reticle: just past the index fingertip, or the centre with no hand.
    Item {
        width: Math.min(parent.width, parent.height) / 9; height: width
        x: (screen.c.x !== undefined ? screen.c.x : 0.5) * parent.width - width / 2
        y: (screen.c.y !== undefined ? screen.c.y : 0.5) * parent.height - height / 2
        Rectangle {
            anchors.fill: parent; radius: width / 2
            color: "transparent"; border.width: 4 * screen.u; border.color: "white"
        }
        Rectangle {
            anchors.fill: parent; anchors.margins: -8 * screen.u; radius: width / 2
            color: "transparent"; border.width: 6 * screen.u; border.color: screen.current
        }
        SequentialAnimation on scale {
            loops: Animation.Infinite
            NumberAnimation { to: 1.08; duration: 900; easing.type: Easing.InOutSine }
            NumberAnimation { to: 1.0; duration: 900; easing.type: Easing.InOutSine }
        }
    }

    TopBar { width: parent.width; title: "Color Finder"; accent: "#ffd24d" }

    GlassPanel {
        id: panel
        anchors.left: parent.left; anchors.leftMargin: 12 * screen.u
        anchors.top: parent.top; anchors.topMargin: 70 * screen.u
        width: 250 * screen.u
        height: col.implicitHeight + 32 * screen.u
        Column {
            id: col
            x: 18 * screen.u; y: 16 * screen.u
            width: parent.width - 36 * screen.u
            spacing: 10 * screen.u
            Text {
                width: parent.width
                text: screen.c.tracking ? "Point your finger at any colour" : "Point at something, or hold it in the circle"
                color: "#c9d1e3"; font.pixelSize: 13 * screen.u; wrapMode: Text.WordWrap
            }
            Row {
                spacing: 14 * screen.u
                Rectangle {
                    width: 78 * screen.u; height: width; radius: width / 2
                    color: screen.current
                    border.width: 3 * screen.u; border.color: "white"
                    Behavior on color { ColorAnimation { duration: 150 } }
                }
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    Text { text: screen.c.name; color: "white"; font.pixelSize: 26 * screen.u; font.bold: true }
                    Text { text: screen.c.hex.toUpperCase(); color: "#c9d1e3"; font.pixelSize: 15 * screen.u; font.family: "DejaVu Sans Mono" }
                }
            }
            Repeater {
                model: [["R", "r", "#ff4d6d"], ["G", "g", "#3ddc97"], ["B", "b", "#4d9bff"]]
                Row {
                    required property var modelData
                    spacing: 8 * screen.u
                    Text { text: modelData[0]; color: modelData[2]; font.pixelSize: 14 * screen.u; font.bold: true; width: 14 * screen.u }
                    Rectangle {
                        width: 150 * screen.u; height: 10 * screen.u; radius: height / 2
                        color: Qt.rgba(1, 1, 1, 0.1)
                        anchors.verticalCenter: parent.verticalCenter
                        Rectangle {
                            width: parent.width * screen.c[modelData[1]] / 255; height: parent.height; radius: height / 2
                            color: modelData[2]
                            Behavior on width { NumberAnimation { duration: 120 } }
                        }
                    }
                    Text { text: screen.c[modelData[1]]; color: "#c9d1e3"; font.pixelSize: 13 * screen.u }
                }
            }
        }
    }

}
