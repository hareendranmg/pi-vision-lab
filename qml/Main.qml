import QtQuick
import QtQuick.Window
import PiVision
import "components"

Window {
    id: win
    width: startSize[0]
    height: startSize[1]
    visible: true
    visibility: kiosk ? Window.FullScreen : Window.Windowed
    color: "#05070d"
    title: "Pi Vision Lab"

    // Layout unit: 1u = 1px on the 800x480 Raspberry Pi touch display.
    readonly property real u: Math.min(width / 800, height / 480)
    property string screen: "home"
    readonly property var accents: ({ home: "#39e1ff", objects: "#39e1ff", face: "#ff5fd2", color: "#ffd24d" })
    readonly property color accent: accents[screen]

    onScreenChanged: backend.mode = screen

    CameraView {
        anchors.fill: parent
    }

    // Dim the live video behind the home menu.
    Rectangle {
        anchors.fill: parent
        color: "#05070d"
        opacity: win.screen === "home" ? 0.62 : 0
        Behavior on opacity { NumberAnimation { duration: 350 } }
    }

    Loader {
        id: page
        anchors.fill: parent
        source: {
            const names = { home: "Home", objects: "Objects", face: "Face", color: "Color" }
            return "screens/" + names[win.screen] + "Screen.qml"
        }
        onLoaded: fadeIn.restart()
        NumberAnimation { id: fadeIn; target: page.item; property: "opacity"; from: 0; to: 1; duration: 260 }
    }

    Presenter {
        z: 50
    }

    HandHint {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 10 * win.u
        visible: win.screen === "home"
    }

    AirCursor {
        accent: win.accent
        z: 100
    }

    Connections {
        target: backend
        function onGoHome() { win.screen = "home" }
    }
}
