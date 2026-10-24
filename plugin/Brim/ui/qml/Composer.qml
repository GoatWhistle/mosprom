import QtQuick 2.7

Item {
    id: root
    property var view: ({})
    property var c: ({})
    property alias text: input.text
    signal send()
    signal attach()
    signal stop()
    signal detach(int index)
    signal skillChosen(string name)

    height: box.height + hint.height + 6

    function focusInput() {
        input.forceActiveFocus()
    }

    Rectangle {
        id: box
        width: parent.width
        height: Math.min(200, Math.max(84, input.contentHeight + 62 + (chips.visible ? chips.height + 6 : 0)))
        radius: 6
        color: root.c.panel
        border.width: 1
        border.color: input.activeFocus ? root.c.accent : root.c.line
        Behavior on border.color { ColorAnimation { duration: 120 } }

        Column {
            anchors.fill: parent
            anchors.margins: 10
            anchors.bottomMargin: 6
            spacing: 6

            Flow {
                id: chips
                width: parent.width
                spacing: 6
                visible: root.view.attachments.length > 0
                Repeater {
                    model: root.view.attachments
                    delegate: AttachmentChip {
                        name: modelData.name
                        removable: true
                        c: root.c
                        onRemoved: root.detach(index)
                    }
                }
            }

            Flickable {
                width: parent.width
                height: parent.height - 40 - (chips.visible ? chips.height + 6 : 0)
                contentHeight: input.contentHeight
                clip: true
                TextEdit {
                    font.family: "Onest"
                    id: input
                    width: parent.width
                    wrapMode: TextEdit.Wrap
                    selectByMouse: true
                    color: root.c.text
                    font.pixelSize: 14
                    selectionColor: root.c.accent
                    selectedTextColor: root.c.actionText
                    activeFocusOnTab: true
                    focus: true
                    Keys.onPressed: {
                        if ((event.key === Qt.Key_Return || event.key === Qt.Key_Enter) && !(event.modifiers & Qt.ShiftModifier)) {
                            event.accepted = true
                            root.send()
                        }
                    }
                    BrimText {
                        visible: input.text === ""
                        text: root.view.t.placeholder
                        color: root.c.muted
                        font.pixelSize: 14
                    }
                }
            }

            Item {
                width: parent.width
                height: 34
                IconButton {
                    id: attachButton
                    anchors.left: parent.left
                    glyph: "attach"
                    palette_: root.c
                    enabledButton: !root.view.busy
                    onClicked: root.attach()
                }
                SkillPicker {
                    anchors.left: attachButton.right
                    anchors.leftMargin: 6
                    view: root.view
                    c: root.c
                    visible: (root.view.skill_options || []).length > 0
                    onChosen: root.skillChosen(name)
                }
                IconButton {
                    anchors.right: parent.right
                    visible: !root.view.run_active
                    glyph: "send"
                    primary: true
                    palette_: root.c
                    enabledButton: !root.view.busy
                    onClicked: root.send()
                }
                IconButton {
                    anchors.right: parent.right
                    visible: !!root.view.run_active
                    glyph: "stop"
                    palette_: root.c
                    enabledButton: !root.view.stopping
                    onClicked: root.stop()
                }
            }
        }
    }

    BrimText {
        id: hint
        anchors.top: box.bottom
        anchors.topMargin: 6
        anchors.horizontalCenter: parent.horizontalCenter
        text: root.view.t.composer_hint
        color: root.c.muted
        font.pixelSize: 11
    }
}
