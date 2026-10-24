import QtQuick 2.7

Item {
    id: root
    property var entry: ({})
    property var t: ({})
    property var c: ({})
    property bool mine: entry.kind === "user"
    property real maxBubble: Math.max(220, width * (mine ? 0.82 : 0.94))

    function themed(html) {
        return (html || "").replace(/#c0de01/g, c.selected).replace(/#c0de02/g, c.line)
            .replace(/#c0de03/g, c.accentText).replace(/#c0de04/g, c.muted)
    }

    width: parent ? parent.width : 300
    height: bubble.height

    BrimText {
        id: measure
        visible: false
        text: root.mine ? root.entry.text || "" : ""
        font.pixelSize: 14
    }

    Rectangle {
        id: bubble
        x: root.mine ? root.width - width : 0
        width: root.mine ? Math.min(root.maxBubble, Math.max(measure.implicitWidth, chips.visible ? 200 : 0) + 28)
                         : root.maxBubble
        height: content.height + 20
        radius: 6
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
                textFormat: root.mine ? TextEdit.PlainText : TextEdit.RichText
                text: root.mine ? root.entry.text || "" : root.themed(root.entry.html || "")
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
