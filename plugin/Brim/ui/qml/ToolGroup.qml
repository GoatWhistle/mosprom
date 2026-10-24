import QtQuick 2.7

Item {
    id: root
    property var entry: ({})
    property var t: ({})
    property var c: ({})
    property bool expanded: false
    signal toggled(bool value)

    width: parent ? parent.width : 300
    height: header.height + reveal
    clip: true
    property real reveal: expanded ? list.height : 0
    Behavior on reveal { NumberAnimation { duration: 200; easing.type: Easing.OutQuint } }

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
            BrimText {
                text: (root.t.agent_actions || "") + " · " + (root.entry.items || []).length
                color: root.c.muted
                font.pixelSize: 12
            }
            BrimText {
                text: "˅"
                color: root.c.muted
                font.pixelSize: 12
                rotation: root.expanded ? 180 : 0
                Behavior on rotation { NumberAnimation { duration: 160 } }
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
        visible: root.reveal > 0
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
