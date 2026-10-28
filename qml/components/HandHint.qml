import QtQuick

// Bottom-centre hint that teaches the gestures and echoes the detected pose.
Rectangle {
    id: hint
    readonly property real u: win.u
    readonly property bool hand: !!(backend.vision.hand && backend.vision.hand.present)
    readonly property string gesture: hand ? backend.vision.hand.gesture : ""
    implicitWidth: row.implicitWidth + 28 * u
    implicitHeight: 38 * u
    radius: height / 2
    color: Qt.rgba(0, 0, 0, 0.55)
    border.width: 1 * u
    border.color: hand ? "#7cff9b" : Qt.rgba(1, 1, 1, 0.15)

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 10 * hint.u
        Icon {
            name: "hand"; color: hint.hand ? "#7cff9b" : "#a9b3c9"
            width: 20 * hint.u; height: width
            anchors.verticalCenter: parent.verticalCenter
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            color: "white"
            font.pixelSize: 14 * hint.u
            textFormat: Text.StyledText
            text: !hint.hand ? "Raise your hand to take control, or just touch the screen"
                 : (hint.gesture ? "<b>" + hint.gesture + "</b>   ·   " : "") + "pinch to tap   ·   hold a fist to go home"
        }
    }
}
