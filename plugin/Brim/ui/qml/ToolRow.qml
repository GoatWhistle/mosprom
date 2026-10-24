import QtQuick 2.7

Rectangle {
    id: root
    property var entry: ({})
    property var t: ({})
    property var c: ({})
    property bool failed: entry.status === "failed" || entry.status === "rejected"
    property string statusKey: "tool_" + entry.status
    property bool running: entry.status === "running"
    property bool ok: entry.status === "ok"

    width: parent ? parent.width : 300
    height: column.height + 12
    radius: 0
    color: failed ? Qt.rgba(1, 0.45, 0.4, 0.08) : "transparent"
    border.width: failed ? 1 : 0
    border.color: c.danger

    Column {
        id: column
        x: 12
        y: 6
        width: parent.width - 24
        spacing: 2

        Row {
            spacing: 8
            Item {
                width: 12
                height: 12
                anchors.verticalCenter: parent ? parent.verticalCenter : undefined
                Spinner {
                    anchors.fill: parent
                    visible: root.running
                    running: root.running
                    color: root.c.accent
                    track: Qt.rgba(0.5, 0.5, 0.5, 0.25)
                }
                BrimText {
                    id: mark
                    anchors.centerIn: parent
                    visible: !root.running
                    text: root.failed ? "✕" : (root.ok ? "✓" : "•")
                    color: root.failed ? root.c.danger : (root.ok ? root.c.ok : root.c.muted)
                    font.pixelSize: 12
                    font.bold: true
                }
            }
            BrimText {
                text: (root.entry.server && root.entry.server !== "brim" ? root.entry.server + " · " : "")
                      + (root.entry.server === "brim" ? (root.t["tool_" + root.entry.tool] || root.entry.tool) : root.entry.tool)
                      + " · " + (root.t[root.statusKey] || root.entry.status)
                color: root.failed ? root.c.danger : root.c.muted
                font.pixelSize: 12
            }
        }
        Item {
            x: 20
            width: parent.width - 20
            height: root.running ? 3 : 0
            visible: root.running
            clip: true
            Row {
                id: dashes
                spacing: 6
                Repeater {
                    model: Math.ceil(dashes.parent.width / 14) + 2
                    Rectangle { width: 8; height: 3; radius: 1.5; color: root.c.accent; opacity: 0.7 }
                }
                NumberAnimation on x {
                    running: root.running
                    loops: Animation.Infinite
                    from: -14
                    to: 0
                    duration: 450
                }
            }
        }
        SelectableText {
            x: 15
            width: parent.width - 15
            visible: !!root.entry.detail
            text: root.entry.detail || ""
            textColor: root.failed ? root.c.danger : root.c.muted
            font.pixelSize: 11
        }
    }
}
