import QtQuick
import "../components"

Item {
    id: home
    readonly property real u: win.u
    // Leave the right-hand fifth of the screen for the presenter.
    readonly property real area: width * 0.8

    Column {
        id: header
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.horizontalCenterOffset: -home.width * 0.1
        y: 30 * home.u
        spacing: 4 * home.u
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Pi Vision Lab"
            color: "white"
            font.pixelSize: 38 * home.u
            font.bold: true
            font.letterSpacing: 1.5 * home.u
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Edge AI on a Raspberry Pi 4  ·  control it with your hand"
            color: "#8fe9ff"
            font.pixelSize: 15 * home.u
        }
    }

    Row {
        id: tiles
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.horizontalCenterOffset: -home.width * 0.1
        // Centre the tiles between the header and the gesture hint.
        y: header.y + header.height + (home.height - header.y - header.height - 60 * home.u - height) / 2
        spacing: 20 * home.u
        readonly property real tw: (Math.min(home.area, 640 * home.u) - 2 * 20 * home.u) / 3
        readonly property real th: 240 * home.u

        Tile {
            width: tiles.tw; height: tiles.th
            title: "Object Finder"; icon: "objects"; accent: "#39e1ff"
            subtitle: "Spots 80 kinds of everyday things, live"
            onClicked: win.screen = "objects"
        }
        Tile {
            width: tiles.tw; height: tiles.th
            title: "Face Magic"; icon: "face"; accent: "#ff5fd2"
            subtitle: "Reads your expression and adds AR effects"
            onClicked: win.screen = "face"
        }
        Tile {
            width: tiles.tw; height: tiles.th
            title: "Color Finder"; icon: "color"; accent: "#ffd24d"
            subtitle: "Show it anything and it names the colour"
            onClicked: win.screen = "color"
        }
    }

    // Power: opens the shut-down confirmation (Main.qml's PowerDialog).
    Rectangle {
        anchors.right: parent.right; anchors.top: parent.top
        anchors.margins: 14 * home.u
        width: 46 * home.u; height: width; radius: width / 2
        color: powerArea.containsMouse ? Qt.rgba(1, 0.42, 0.29, 0.28) : Qt.rgba(0, 0, 0, 0.45)
        border.width: 1.5 * home.u
        border.color: powerArea.containsMouse ? "#ff6b4a" : Qt.rgba(1, 1, 1, 0.25)
        scale: powerArea.pressed ? 0.92 : (powerArea.containsMouse ? 1.08 : 1)
        Behavior on scale { NumberAnimation { duration: 120 } }
        Icon {
            anchors.centerIn: parent
            name: "power"
            color: powerArea.containsMouse ? "#ff8a65" : "#c9d1e3"
            width: 24 * home.u; height: width
            stroke: 2.5 * home.u
        }
        MouseArea {
            id: powerArea
            anchors.fill: parent
            anchors.margins: -8 * home.u  // forgiving target for the air cursor
            hoverEnabled: true
            onClicked: powerDialog.asking = true
        }
    }
}
