import QtQuick

Rectangle {
    readonly property real u: win.u
    radius: 20 * u
    color: Qt.rgba(0.05, 0.07, 0.12, 0.82)
    border.width: 1.2 * u
    border.color: Qt.rgba(1, 1, 1, 0.12)
}
