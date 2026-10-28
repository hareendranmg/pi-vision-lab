import QtQuick
import "../components"

// Effects are rendered into the camera frame by app/face_fx.py; this screen
// shows the mood read-out and picks the effect.
Item {
    id: screen
    readonly property real u: win.u
    readonly property var face: backend.vision.face || { present: false }
    readonly property bool present: !!face.present

    readonly property var emotionInfo: ({
        neutral: ["Neutral", "#a9b3c9", "Try a big smile!"],
        happy: ["Happy", "#7cff9b", "That smile is contagious"],
        surprised: ["Surprised", "#ffd24d", "Whoa! Eyebrows up!"],
        winking: ["Winking", "#ff5fd2", "Smooth wink detected"],
        sleepy: ["Sleepy", "#8fa8ff", "Eyes closed... wake up!"],
        talking: ["Talking", "#39e1ff", "I see you saying something"]
    })

    TopBar { width: parent.width; title: "Face Magic"; accent: "#ff5fd2" }

    GlassPanel {
        id: moodPanel
        x: 12 * screen.u; y: 70 * screen.u
        width: 200 * screen.u
        height: moodCol.implicitHeight + 28 * screen.u
        readonly property var info: screen.emotionInfo[screen.present ? screen.face.emotion : "neutral"]
        Column {
            id: moodCol
            x: 14 * screen.u; y: 14 * screen.u
            width: parent.width - 28 * screen.u
            spacing: 6 * screen.u
            Text { text: "MOOD"; color: "#8d97ad"; font.pixelSize: 12 * screen.u; font.bold: true; font.letterSpacing: 2 }
            Text {
                text: screen.present ? moodPanel.info[0] : "No face yet"
                color: screen.present ? moodPanel.info[1] : "#a9b3c9"
                font.pixelSize: 28 * screen.u; font.bold: true
            }
            Text {
                width: parent.width
                text: screen.present ? moodPanel.info[2] : "Look at the camera"
                color: "#c9d1e3"; font.pixelSize: 13 * screen.u; wrapMode: Text.WordWrap
            }
            Item { width: 1; height: 4 * screen.u }
            Repeater {
                model: [["happy", "Smile"], ["surprised", "Surprise"], ["mouthOpen", "Mouth open"], ["eyesClosed", "Eyes closed"], ["wink", "Wink"]]
                delegate: Column {
                    required property var modelData
                    width: moodCol.width
                    spacing: 2 * screen.u
                    readonly property real v: screen.present && screen.face.scores ? screen.face.scores[modelData[0]] : 0
                    Text { text: modelData[1]; color: "#a9b3c9"; font.pixelSize: 12 * screen.u }
                    Rectangle {
                        width: parent.width; height: 7 * screen.u; radius: height / 2
                        color: Qt.rgba(1, 1, 1, 0.1)
                        Rectangle {
                            width: parent.width * parent.parent.v; height: parent.height; radius: height / 2
                            color: "#ff5fd2"
                            Behavior on width { NumberAnimation { duration: 120 } }
                        }
                    }
                }
            }
        }
    }

    Flow {  // wraps into two rows, clear of the presenter on the right
        anchors.left: parent.left; anchors.leftMargin: 12 * screen.u
        anchors.bottom: parent.bottom; anchors.bottomMargin: 12 * screen.u
        width: parent.width * 0.74
        spacing: 8 * screen.u
        Repeater {
            model: [["masquerade", "Masquerade"], ["crown", "Crown"], ["shades", "Shades"],
                    ["glam", "Glam"], ["iceeyes", "Ice eyes"], ["mesh", "AI mesh"], ["none", "None"]]
            PillButton {
                required property var modelData
                text: modelData[1]
                accent: "#ff5fd2"
                selected: backend.faceEffect === modelData[0]
                onClicked: backend.faceEffect = modelData[0]
            }
        }
    }
}
