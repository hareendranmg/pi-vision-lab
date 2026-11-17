import QtQuick

// Shut-down confirmation, then a "Shutting down" screen (app/power.py does the work).
// Opened by setting `asking`; it cancels itself after 20 s, or on the fist-to-home gesture.
Item {
    id: dlg
    anchors.fill: parent
    readonly property real u: win.u
    property bool asking: false
    readonly property string state_: power ? power.state : "idle"
    visible: asking || state_ !== "idle"

    function close() {
        asking = false
        if (power) power.reset()
    }

    Timer {
        running: dlg.asking && dlg.state_ === "idle"
        interval: 20000
        onTriggered: dlg.close()
    }

    Rectangle {  // dim everything and swallow clicks behind the dialog
        anchors.fill: parent
        color: "black"
        opacity: dlg.state_ === "shutting" ? 0.92 : 0.7
        Behavior on opacity { NumberAnimation { duration: 600 } }
        MouseArea { anchors.fill: parent; hoverEnabled: true }
    }

    GlassPanel {
        anchors.centerIn: parent
        width: Math.min(440 * dlg.u, parent.width * 0.9)
        height: col.implicitHeight + 48 * dlg.u
        border.color: dlg.state_ === "failed" ? "#ff6b6b" : "#ff8a65"

        Column {
            id: col
            x: 24 * dlg.u; y: 24 * dlg.u
            width: parent.width - 48 * dlg.u
            spacing: 14 * dlg.u

            Icon {
                anchors.horizontalCenter: parent.horizontalCenter
                name: "power"; color: "#ff8a65"
                width: 52 * dlg.u; height: width
                stroke: 4 * dlg.u
                RotationAnimation on rotation {
                    running: dlg.state_ === "shutting"; loops: Animation.Infinite
                    from: 0; to: 360; duration: 1600
                }
            }
            Text {
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                text: dlg.state_ === "shutting" ? "Shutting down…"
                    : dlg.state_ === "failed" ? "Couldn't shut down" : "Shut down the Pi?"
                color: "white"; font.pixelSize: 24 * dlg.u; font.bold: true
            }
            Text {
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                color: dlg.state_ === "failed" ? "#ffb3b3" : "#c9d1e3"
                font.pixelSize: 14 * dlg.u
                text: dlg.state_ === "shutting"
                      ? "Wait until the screen goes dark and the green light on the Pi stops flashing, then you can unplug it."
                      : dlg.state_ === "failed" ? power.error
                      : "The demo will close and the Raspberry Pi will power off. To start it again, unplug the power and plug it back in."
            }
            Row {
                visible: dlg.state_ !== "shutting"
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 16 * dlg.u
                PillButton {
                    text: dlg.state_ === "failed" ? "Close" : "Cancel"
                    accent: "#39e1ff"
                    implicitWidth: 150 * dlg.u
                    onClicked: dlg.close()
                }
                PillButton {
                    visible: dlg.state_ === "idle"
                    text: "Shut down"
                    icon: "power"
                    accent: "#ff6b4a"
                    selected: true
                    implicitWidth: 170 * dlg.u
                    onClicked: power.shutdown()
                }
            }
        }
    }

    Connections {
        target: backend
        function onGoHome() { if (dlg.state_ !== "shutting") dlg.close() }
    }
}
