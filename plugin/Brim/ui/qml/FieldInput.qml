import QtQuick 2.7

Column {
    id: root
    property string label: ""
    property string value: text.text
    property string initial: ""
    property string hint: ""
    property bool secret: false
    property var c: ({})

    spacing: 4
    onInitialChanged: text.text = initial

    function reset() {
        text.text = ""
    }

    BrimText {
        text: root.label
        color: root.c.muted
        font.pixelSize: 12
    }
    Rectangle {
        width: parent.width
        height: 34
        radius: 6
        color: root.c.bg
        border.width: 1
        border.color: text.activeFocus ? root.c.accent : root.c.line

        TextInput {
            font.family: "Onest"
            id: text
            anchors.fill: parent
            anchors.leftMargin: 10
            anchors.rightMargin: 10
            verticalAlignment: TextInput.AlignVCenter
            clip: true
            selectByMouse: true
            color: root.c.text
            font.pixelSize: 13
            echoMode: root.secret ? TextInput.Password : TextInput.Normal
            activeFocusOnTab: true
        }
        BrimText {
            anchors.fill: parent
            anchors.leftMargin: 10
            verticalAlignment: Text.AlignVCenter
            visible: text.text === "" && root.hint !== ""
            text: root.hint
            color: root.c.muted
            font.pixelSize: 12
            elide: Text.ElideRight
        }
    }
}
