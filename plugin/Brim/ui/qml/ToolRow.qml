import QtQuick 2.7

Rectangle {
    id: root
    property var entry: ({})
    property var t: ({})
    property var c: ({})
    property string statusKey: entry.status === "ok" ? "tool_ok" : (entry.status === "failed" ? "tool_failed" : "tool_running")
    property bool running: entry.status !== "ok" && entry.status !== "failed"

    width: parent ? parent.width : 300
    height: column.height + 12
    radius: 10
    color: entry.status === "failed" ? Qt.rgba(1, 0.45, 0.4, 0.08) : "transparent"
    border.width: entry.status === "failed" ? 1 : 0
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
                anchors.verticalCenter: parent.verticalCenter
                color: root.entry.status === "failed" ? root.c.danger : (root.entry.status === "ok" ? root.c.ok : root.c.accent)
                SequentialAnimation on opacity {
                    running: root.running
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.3; duration: 600 }
                    NumberAnimation { to: 1.0; duration: 600 }
                }
            }
            Text {
                text: (root.t["tool_" + root.entry.tool] || root.entry.tool) + " · " + (root.t[root.statusKey] || "")
                color: root.entry.status === "failed" ? root.c.danger : root.c.muted
                font.pixelSize: 12
            }
        }
        SelectableText {
            x: 15
            width: parent.width - 15
            visible: !!root.entry.detail
            text: root.entry.detail || ""
            textColor: root.c.muted
            font.pixelSize: 11
        }
        SelectableText {
            x: 15
            width: parent.width - 15
            visible: !!root.entry.error
            text: root.entry.error || ""
            textColor: root.c.danger
            font.pixelSize: 12
        }
    }
}
