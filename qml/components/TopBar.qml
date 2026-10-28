import QtQuick

// Header for the feature screens: home button, title, live stats.
Item {
    id: bar
    property string title
    property color accent: "#39e1ff"
    readonly property real u: win.u
    height: 64 * u

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0; color: Qt.rgba(0, 0, 0, 0.6) }
            GradientStop { position: 1; color: "transparent" }
        }
    }

    PillButton {
        id: home
        x: 12 * bar.u
        anchors.verticalCenter: parent.verticalCenter
        icon: "back"
        text: "Home"
        accent: bar.accent
        onClicked: win.screen = "home"
    }

    Text {
        anchors.left: home.right; anchors.leftMargin: 16 * bar.u
        anchors.verticalCenter: parent.verticalCenter
        text: bar.title
        color: "white"
        font.pixelSize: 22 * bar.u
        font.bold: true
        style: Text.Raised; styleColor: "#80000000"
    }

    Row {
        anchors.right: parent.right; anchors.rightMargin: 14 * bar.u
        anchors.verticalCenter: parent.verticalCenter
        spacing: 8 * bar.u
        Chip { text: (backend.vision.fps || 0).toFixed(0) + " fps"; dim: true }
    }
}
