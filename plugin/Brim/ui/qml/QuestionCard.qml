import QtQuick 2.7

Rectangle {
    id: root
    property var entry: ({"questions": []})
    property var t: ({})
    property var c: ({})
    property bool active: false
    signal picked(int index, string option)

    width: parent ? parent.width : 300
    height: column.height + 28
    radius: 14
    color: c.panel
    border.width: active ? 2 : 1
    border.color: active ? c.accent : c.line

    Column {
        id: column
        x: 16
        y: 14
        width: parent.width - 32
        spacing: 8

        Text {
            text: root.t.question || ""
            color: root.c.accentText
            font.bold: true
            font.pixelSize: 13
        }
        Repeater {
            model: root.entry.questions || []
            delegate: Column {
                property int questionIndex: index
                width: column.width
                spacing: 6
                SelectableText {
                    width: parent.width
                    text: ((root.entry.questions || []).length > 1 ? (index + 1) + ". " : "") + modelData.text
                    textColor: root.c.text
                }
                Flow {
                    width: parent.width
                    spacing: 6
                    visible: root.active && (modelData.options || []).length > 0
                    Repeater {
                        model: modelData.options || []
                        delegate: BrimButton {
                            text: modelData
                            palette_: root.c
                            onClicked: root.picked(questionIndex, modelData)
                        }
                    }
                }
            }
        }
        Text {
            visible: root.active
            width: parent.width
            wrapMode: Text.Wrap
            text: root.t.answer_hint || ""
            color: root.c.muted
            font.pixelSize: 12
        }
        SelectableText {
            visible: !!root.entry.answer
            width: parent.width
            text: (root.t.answered || "") + ": " + (root.entry.answer || "")
            textColor: root.c.muted
            font.pixelSize: 12
        }
    }
}
