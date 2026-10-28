import QtQuick

// Rounded button sized for fingers and air-pinches.
Rectangle {
    id: pill
    property string text
    property string icon: ""
    property color accent: "#39e1ff"
    property bool selected: false
    property bool clickable: true
    readonly property real u: win.u
    signal clicked()

    implicitWidth: row.implicitWidth + 36 * u
    implicitHeight: 48 * u
    radius: height / 2
    opacity: clickable ? 1 : 0.45
    color: selected ? accent : (area.containsMouse ? Qt.rgba(0.16 + accent.r * 0.25, 0.18 + accent.g * 0.25, 0.24 + accent.b * 0.25, 0.95)
                                                   : Qt.rgba(0.08, 0.10, 0.16, 0.85))
    border.width: 1.5 * u
    border.color: selected || area.containsMouse ? accent : Qt.rgba(1, 1, 1, 0.18)
    scale: area.pressed ? 0.93 : (area.containsMouse ? 1.05 : 1)
    Behavior on scale { NumberAnimation { duration: 120 } }
    Behavior on color { ColorAnimation { duration: 120 } }

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 8 * pill.u
        Icon {
            visible: pill.icon !== ""
            name: pill.icon
            color: pill.selected ? "#0b0e17" : pill.accent
            width: 22 * pill.u; height: width
            anchors.verticalCenter: parent.verticalCenter
        }
        Text {
            text: pill.text
            color: pill.selected ? "#0b0e17" : "white"
            font.pixelSize: 16 * pill.u
            font.bold: true
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        anchors.margins: -6 * pill.u  // forgiving hit area for the air cursor
        hoverEnabled: true
        enabled: pill.clickable
        onClicked: pill.clicked()
    }
}
