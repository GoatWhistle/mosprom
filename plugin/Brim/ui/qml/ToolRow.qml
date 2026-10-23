import QtQuick 2.7

Rectangle {
    id: root
    property var entry: ({})
    property var t: ({})
    property var c: ({})
    property string statusKey: entry.status === "ok" ? "tool_ok" : (entry.status === "failed" ? "tool_failed" : "tool_running")

    width: parent ? parent.width : 300
    height: column.height + 16
    radius: 6
    color: c.panel
    border.width: 1
    border.color: entry.status === "failed" ? c.danger : c.line

    Column {
        id: column
        x: 12
        y: 8
        width: parent.width - 24
        spacing: 2

        Row {
            spacing: 8
            Rectangle {
                width: 8
                height: 8
                radius: 4
                anchors.verticalCenter: parent.verticalCenter
                color: root.entry.status === "failed" ? root.c.danger : (root.entry.status === "ok" ? root.c.ok : root.c.accent)
            }
            Text {
                text: (root.t["tool_" + root.entry.tool] || root.entry.tool) + " — " + (root.t[root.statusKey] || "")
                color: root.c.text
                font.pixelSize: 13
            }
        }
        SelectableText {
            width: parent.width
            visible: !!root.entry.detail
            text: root.entry.detail || ""
            textColor: root.c.muted
            font.pixelSize: 12
        }
        SelectableText {
            width: parent.width
            visible: !!root.entry.error
            text: root.entry.error || ""
            textColor: root.c.danger
            font.pixelSize: 12
        }
    }
}
