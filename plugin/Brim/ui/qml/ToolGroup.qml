import QtQuick 2.7

Item {
    id: root
    property var entry: ({})
    property var t: ({})
    property var c: ({})
    property bool expanded: false
    signal toggled(bool value)

    width: parent ? parent.width : 300
    height: header.height + (expanded ? list.height : 0)

    Rectangle {
        id: header
        width: parent.width
        height: 30
        radius: 15
        color: area.containsMouse ? root.c.hover : "transparent"
        Row {
            anchors.verticalCenter: parent.verticalCenter
            x: 12
            spacing: 8
            Rectangle {
                width: 7
                height: 7
                radius: 4
                anchors.verticalCenter: parent.verticalCenter
                color: root.c.ok
            }
            Text {
                text: (root.t.agent_actions || "") + " · " + (root.entry.items || []).length
                color: root.c.muted
                font.pixelSize: 12
            }
            Text {
                text: root.expanded ? "˄" : "˅"
                color: root.c.muted
                font.pixelSize: 12
            }
        }
        MouseArea {
            id: area
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.toggled(!root.expanded)
        }
    }

    Column {
        id: list
        visible: root.expanded
        anchors.top: header.bottom
        width: parent.width
        Repeater {
            model: root.entry.items || []
            delegate: ToolRow {
                width: list.width
                entry: modelData
                t: root.t
                c: root.c
            }
        }
    }
}
