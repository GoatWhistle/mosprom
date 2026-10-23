import QtQuick 2.7

Rectangle {
    id: root
    property var entry: ({})
    property var t: ({})
    property var c: ({})
    property bool failed: entry.status === "failed" || entry.status === "rejected"
    property string statusKey: "tool_" + entry.status
    property bool running: entry.status === "running"

    width: parent ? parent.width : 300
    height: column.height + 12
    radius: 10
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
            Rectangle {
                id: dot
                width: 7
                height: 7
                radius: 4
                anchors.verticalCenter: parent ? parent.verticalCenter : undefined
                color: root.failed ? root.c.danger : (root.entry.status === "ok" ? root.c.ok : (root.running ? root.c.accent : root.c.muted))
                SequentialAnimation on opacity {
                    running: root.running
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.3; duration: 600 }
                    NumberAnimation { to: 1.0; duration: 600 }
                }
            }
            Text {
                text: (root.entry.server && root.entry.server !== "brim" ? root.entry.server + " · " : "")
                      + (root.entry.server === "brim" ? (root.t["tool_" + root.entry.tool] || root.entry.tool) : root.entry.tool)
                      + " · " + (root.t[root.statusKey] || root.entry.status)
                color: root.failed ? root.c.danger : root.c.muted
                font.pixelSize: 12
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
