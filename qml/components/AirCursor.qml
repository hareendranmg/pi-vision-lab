import QtQuick
import QtQuick.Shapes

// On-screen pointer driven by the tracked hand. The centre fills as the
// fingers close (so a click never surprises you), it ripples on the click, and
// an orange arc counts down while a fist is held to go home.
Item {
    id: cursor
    readonly property real u: win.u
    property color accent: "#39e1ff"
    readonly property real fill: backend.pinchLevel
    readonly property real home: backend.homeProgress
    width: 46 * u; height: width
    x: backend.cursorX * parent.width - width / 2
    y: backend.cursorY * parent.height - height / 2
    opacity: backend.cursorVisible ? 1 : 0
    Behavior on opacity { NumberAnimation { duration: 200 } }

    Rectangle {  // outer ring
        anchors.centerIn: parent
        width: parent.width * (backend.pinching ? 0.78 : 1); height: width
        radius: width / 2
        color: Qt.rgba(1, 1, 1, 0.10)
        border.width: 3 * cursor.u
        border.color: backend.pinching ? cursor.accent : "white"
        Behavior on width { NumberAnimation { duration: 90 } }
    }
    Rectangle {  // fill grows as thumb and index approach
        anchors.centerIn: parent
        width: (10 + 26 * cursor.fill) * cursor.u; height: width
        radius: width / 2
        color: cursor.fill >= 1 ? cursor.accent : Qt.rgba(cursor.accent.r, cursor.accent.g, cursor.accent.b, 0.35 + 0.5 * cursor.fill)
        Behavior on width { NumberAnimation { duration: 80 } }
    }
    Rectangle {
        anchors.centerIn: parent
        width: 6 * cursor.u; height: width; radius: width / 2
        color: "white"
    }

    // Fist-to-home countdown.
    Shape {
        anchors.centerIn: parent
        width: cursor.width * 1.7; height: width
        visible: cursor.home > 0
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: "#ffb347"; strokeWidth: 5 * cursor.u
            fillColor: "transparent"; capStyle: ShapePath.RoundCap
            PathAngleArc {
                centerX: cursor.width * 0.85; centerY: cursor.width * 0.85
                radiusX: cursor.width * 0.78; radiusY: radiusX
                startAngle: -90; sweepAngle: 360 * cursor.home
            }
        }
    }
    Rectangle {
        visible: cursor.home > 0
        anchors.top: parent.bottom; anchors.topMargin: 22 * cursor.u
        anchors.horizontalCenter: parent.horizontalCenter
        width: homeLabel.implicitWidth + 16 * cursor.u; height: 24 * cursor.u
        radius: height / 2
        color: Qt.rgba(0, 0, 0, 0.6)
        Text {
            id: homeLabel
            anchors.centerIn: parent
            text: "Going home…"
            color: "#ffb347"; font.pixelSize: 13 * cursor.u; font.bold: true
        }
    }

    Rectangle {
        id: ripple
        anchors.centerIn: parent
        width: cursor.width; height: width; radius: width / 2
        color: "transparent"
        border.width: 3 * cursor.u
        border.color: cursor.accent
        opacity: 0
        ParallelAnimation {
            id: rippleAnim
            NumberAnimation { target: ripple; property: "scale"; from: 0.6; to: 2.4; duration: 420; easing.type: Easing.OutCubic }
            NumberAnimation { target: ripple; property: "opacity"; from: 0.9; to: 0; duration: 420 }
        }
    }

    property bool wasPinching: false
    Connections {
        target: backend
        function onCursorChanged() {
            if (backend.pinching && !cursor.wasPinching) rippleAnim.restart()
            cursor.wasPinching = backend.pinching
        }
    }
}
