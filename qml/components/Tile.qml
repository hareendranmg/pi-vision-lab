import QtQuick

// Big glass card used on the home screen; reacts to touch and to the air cursor.
Item {
    id: tile
    property string title
    property string subtitle
    property string icon
    property color accent: "#39e1ff"
    readonly property real u: win.u
    readonly property bool hot: area.containsMouse
    signal clicked()

    scale: area.pressed ? 0.95 : (hot ? 1.04 : 1.0)
    Behavior on scale { NumberAnimation { duration: 160; easing.type: Easing.OutBack } }

    Rectangle {
        anchors.fill: parent
        anchors.margins: -6 * tile.u
        radius: 26 * tile.u
        color: "transparent"
        border.width: 3 * tile.u
        border.color: tile.accent
        opacity: tile.hot ? 0.45 : 0
        Behavior on opacity { NumberAnimation { duration: 160 } }
    }

    Rectangle {
        anchors.fill: parent
        radius: 22 * tile.u
        border.width: 1.5 * tile.u
        border.color: tile.hot ? tile.accent : Qt.rgba(1, 1, 1, 0.14)
        gradient: Gradient {
            GradientStop { position: 0; color: Qt.rgba(0.10, 0.13, 0.20, 0.88) }
            GradientStop { position: 1; color: Qt.rgba(0.05, 0.06, 0.10, 0.88) }
        }
    }

    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        width: parent.width * 0.35; height: 4 * tile.u; radius: height / 2
        color: tile.accent
    }

    Column {
        anchors.centerIn: parent
        width: parent.width - 32 * tile.u
        spacing: 10 * tile.u
        Icon {
            anchors.horizontalCenter: parent.horizontalCenter
            name: tile.icon
            color: tile.accent
            width: 72 * tile.u; height: width
        }
        Text {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            text: tile.title
            color: "white"
            font.pixelSize: 23 * tile.u
            font.bold: true
        }
        Text {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            text: tile.subtitle
            color: "#a9b3c9"
            font.pixelSize: 13.5 * tile.u
            wrapMode: Text.WordWrap
            maximumLineCount: 3
        }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        onClicked: tile.clicked()
    }
}
