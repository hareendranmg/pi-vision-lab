import QtQuick
import PiVision

// Rajaram: pre-rendered 3D presenter (app/presenter.py drives frames and position)
// plus his typewriter speech bubble.
Item {
    id: root
    anchors.fill: parent
    readonly property real u: win.u
    visible: presenter !== null && presenter.shown

    Item {
        id: ava
        height: root.height * (presenter ? presenter.heightFrac : 0.6)
        width: height * (presenter ? presenter.spriteAspect : 0.55)
        x: (presenter ? presenter.xPos : 1.2) * root.width - width / 2
        y: root.height - height * 0.93

        Rectangle {  // contact shadow under the feet
            width: ava.width * 0.42; height: ava.height * 0.03
            radius: height / 2
            x: (ava.width - width) / 2; y: ava.height * 0.865
            color: "black"; opacity: 0.4
        }
        PresenterView { anchors.fill: parent }
    }

    Item {
        id: bubble
        readonly property string full: presenter ? presenter.bubbleText : ""
        property int shown: 0
        visible: full !== ""
        width: Math.min(320 * root.u, root.width * 0.42)
        height: body.implicitHeight + 34 * root.u
        x: Math.min(ava.x + ava.width * 0.32, root.width) - width
        y: Math.max(70 * root.u, ava.y + ava.height * 0.06 - height * 0.6)

        onFullChanged: shown = 0
        Timer {
            running: bubble.visible && bubble.shown < bubble.full.length
            interval: 22; repeat: true
            onTriggered: bubble.shown = Math.min(bubble.full.length, bubble.shown + 2)
        }
        scale: visible ? 1 : 0.6
        Behavior on scale { NumberAnimation { duration: 180; easing.type: Easing.OutBack } }

        Rectangle {
            anchors.fill: parent
            radius: 16 * root.u
            color: "white"
            border.width: 2 * root.u
            border.color: "#ff5fd2"
        }
        // Tail pointing at the presenter.
        Rectangle {
            width: 18 * root.u; height: width
            rotation: 45
            color: "white"
            border.width: 2 * root.u; border.color: "#ff5fd2"
            x: parent.width - width * 0.6; y: parent.height * 0.55
            z: -1
        }
        Rectangle {  // hides the tail's inner border
            width: 14 * root.u; height: 22 * root.u
            color: "white"
            x: parent.width - width - 2 * root.u; y: parent.height * 0.55 - 2 * root.u
        }
        Text {
            x: 14 * root.u; y: 8 * root.u
            text: "RAJARAM"
            color: "#d0389f"; font.pixelSize: 11 * root.u; font.bold: true; font.letterSpacing: 2
        }
        Text {
            id: body
            x: 14 * root.u; y: 24 * root.u
            width: parent.width - 28 * root.u
            text: bubble.full.substring(0, bubble.shown)
            color: "#141824"
            font.pixelSize: 16 * root.u
            wrapMode: Text.WordWrap
        }
    }
}
