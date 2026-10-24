import QtQuick 2.7
import QtQuick.Window 2.2

Item {
    id: root
    property var activity: null
    property var t: ({})
    property var c: ({})
    property var theme: null
    property bool shown: !!activity
    property real now: Date.now() / 1000
    property real elapsed: activity && activity.since ? Math.max(0, now - activity.since) : 0
    property bool waiting: !!activity && activity.kind === "confirm"
    property bool slow: !!activity && activity.kind === "thinking" && elapsed >= (theme ? theme.slowThinkingSeconds : 60)
    property var progress: null
    signal stop()

    width: parent ? parent.width : 300
    height: shown ? box.height : 0
    opacity: shown ? 1 : 0
    visible: opacity > 0
    clip: true
    Behavior on height { NumberAnimation { duration: root.shown ? (root.theme ? root.theme.durBase : 200) : (root.theme ? root.theme.durExit : 140); easing.type: Easing.OutQuint } }
    Behavior on opacity { NumberAnimation { duration: root.shown ? (root.theme ? root.theme.durBase : 200) : (root.theme ? root.theme.durExit : 140) } }

    function clock(seconds) {
        var s = Math.floor(seconds)
        var m = Math.floor(s / 60)
        var rest = s % 60
        return m + ":" + (rest < 10 ? "0" : "") + rest
    }

    Timer {
        interval: 250
        repeat: true
        running: root.shown
        triggeredOnStart: true
        onTriggered: root.now = Date.now() / 1000
    }

    onWaitingChanged: {
        if (waiting && Window.window && !Window.window.active)
            Window.window.alert(0)
    }

    Rectangle {
        id: box
        width: parent.width
        height: content.height + 16
        radius: 10
        color: root.waiting ? Qt.rgba(1, 0.54, 0.24, 0.10) : root.c.panel
        border.width: 1
        border.color: root.waiting ? root.c.accent : root.c.line
        Behavior on color { ColorAnimation { duration: 160 } }

        Column {
            id: content
            x: 12
            y: 8
            width: parent.width - 24
            spacing: 6

            Item {
                width: parent.width
                height: 20
                Spinner {
                    id: spin
                    width: 16
                    height: 16
                    anchors.verticalCenter: parent.verticalCenter
                    visible: !root.waiting
                    running: root.shown && !root.waiting
                    color: root.activity && root.activity.kind === "stopping" ? root.c.muted : root.c.accent
                    track: Qt.rgba(0.5, 0.5, 0.5, 0.25)
                }
                Rectangle {
                    width: 10
                    height: 10
                    radius: 5
                    x: 3
                    anchors.verticalCenter: parent.verticalCenter
                    visible: root.waiting
                    color: root.c.accent
                    SequentialAnimation on scale {
                        running: root.waiting
                        loops: Animation.Infinite
                        NumberAnimation { to: 1.35; duration: 500; easing.type: Easing.InOutQuad }
                        NumberAnimation { to: 1.0; duration: 500; easing.type: Easing.InOutQuad }
                    }
                }
                BrimText {
                    anchors.left: parent.left
                    anchors.leftMargin: 26
                    anchors.right: meta.left
                    anchors.rightMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    elide: Text.ElideRight
                    text: root.activity ? root.activity.text : ""
                    color: root.waiting ? root.c.accentText : root.c.text
                    font.pixelSize: 13
                    font.bold: root.waiting
                }
                BrimText {
                    id: meta
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    visible: !root.waiting
                    text: (root.activity && root.activity.step > 0 ? (root.t.activity_step || "") + " " + root.activity.step + "  ·  " : "") + root.clock(root.elapsed)
                    color: root.slow ? root.c.accentText : root.c.muted
                    font.family: root.theme ? root.theme.fontMono : "monospace"
                    font.pixelSize: 12
                }
            }

            Item {
                width: parent.width
                height: 4
                visible: !root.waiting
                clip: true
                Rectangle {
                    anchors.fill: parent
                    radius: 2
                    color: root.c.selected
                }
                Rectangle {
                    visible: !!root.progress
                    height: parent.height
                    radius: 2
                    color: root.c.accent
                    width: parent.width * Math.max(0, Math.min(1, (root.progress || {}).fraction || 0))
                    Behavior on width { NumberAnimation { duration: 200 } }
                }
                Rectangle {
                    id: comet
                    visible: !root.progress
                    width: parent.width * 0.3
                    height: parent.height
                    radius: 2
                    color: root.c.accent
                    opacity: 0.8
                    NumberAnimation on x {
                        running: root.shown && !root.progress && !root.waiting
                        loops: Animation.Infinite
                        from: -comet.width
                        to: comet.parent.width
                        duration: root.theme ? root.theme.durTravel * 1.4 : 1400
                        easing.type: Easing.InOutQuad
                    }
                }
            }

            BrimText {
                width: parent.width
                visible: !!root.progress && !!(root.progress || {}).stage
                text: ((root.progress || {}).stage || "") + "  " + Math.round(((root.progress || {}).fraction || 0) * 100) + "%"
                color: root.c.muted
                font.pixelSize: 12
            }

            Item {
                width: parent.width
                height: root.slow ? hint.height + 4 : 0
                visible: root.slow
                BrimText {
                    id: hint
                    anchors.left: parent.left
                    anchors.right: stopButton.left
                    anchors.rightMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    wrapMode: Text.Wrap
                    text: root.t.slow_hint || ""
                    color: root.c.accentText
                    font.pixelSize: 12
                }
                BrimButton {
                    id: stopButton
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.t.stop || "Stop"
                    danger: true
                    palette_: root.c
                    onClicked: root.stop()
                }
            }
        }
    }
}
