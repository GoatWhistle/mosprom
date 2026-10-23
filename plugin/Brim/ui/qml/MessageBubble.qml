import QtQuick 2.7

Item {
    id: root
    property var entry: ({})
    property var t: ({})
    property var c: ({})
    property bool mine: entry.kind === "user"
    property real maxBubble: Math.max(220, width * (mine ? 0.82 : 0.94))

    width: parent ? parent.width : 300
    height: bubble.height

    Text {
        id: measure
        visible: false
        text: root.entry.text || ""
        font.pixelSize: 14
    }

    Rectangle {
        id: bubble
        x: root.mine ? root.width - width : 0
        width: Math.min(root.maxBubble, Math.max(measure.implicitWidth, chips.visible ? 200 : 0) + 28)
        height: content.height + 20
        radius: 14
        color: root.mine ? root.c.userBg : "transparent"
        border.width: 0

        Rectangle {
            visible: !root.mine
            x: -12
            y: 4
            width: 3
            height: 16
            radius: 2
            color: root.c.accent
        }

        Column {
            id: content
            x: 14
            y: 10
            width: parent.width - 28
            spacing: 6

            SelectableText {
                id: body
                width: parent.width
                text: root.entry.text
                textColor: root.mine ? root.c.userText : root.c.text
                font.pixelSize: 14
            }
            Flow {
                id: chips
                width: parent.width
                spacing: 6
                visible: (root.entry.attachments || []).length > 0
                Repeater {
                    model: root.entry.attachments || []
                    delegate: AttachmentChip {
                        name: modelData
                        c: root.c
                    }
                }
            }
        }
    }
}
