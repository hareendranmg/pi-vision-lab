import QtQuick

Rectangle {
    id: chip
    property alias text: label.text
    property color accent: "#39e1ff"
    property bool dim: false
    readonly property real u: win.u
    implicitWidth: label.implicitWidth + 22 * u
    implicitHeight: 30 * u
    radius: height / 2
    color: dim ? Qt.rgba(0, 0, 0, 0.45) : Qt.rgba(accent.r, accent.g, accent.b, 0.22)
    border.width: 1 * u
    border.color: dim ? Qt.rgba(1, 1, 1, 0.15) : accent
    Text {
        id: label
        anchors.centerIn: parent
        color: chip.dim ? "#c9d1e3" : "white"
        font.pixelSize: 13.5 * chip.u
        font.bold: !chip.dim
    }
}
