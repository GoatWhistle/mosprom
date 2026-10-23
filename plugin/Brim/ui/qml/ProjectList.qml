import QtQuick 2.7

Rectangle {
    id: root
    property var view: ({})
    property var c: ({})
    signal chosen(string id)
    signal create()
    signal createFromScene()

    color: c.panel

    Column {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 12

        Row {
            spacing: 8
            Rectangle {
                width: 10
                height: 10
                radius: 5
                anchors.verticalCenter: parent.verticalCenter
                color: root.c.accent
            }
            Text {
                text: "Brim"
                color: root.c.text
                font.pixelSize: 20
                font.bold: true
            }
        }
        BrimButton {
            width: parent.width
            text: "+  " + root.view.t.new_chat
            primary: true
            palette_: root.c
            onClicked: root.create()
        }
        BrimButton {
            width: parent.width
            text: root.view.t.new_from_scene
            palette_: root.c
            enabledButton: !root.view.busy && root.view.switching === null
            onClicked: root.createFromScene()
        }
        Text {
            text: root.view.t.chats
            color: root.c.muted
            font.pixelSize: 11
            font.bold: true
            font.capitalization: Font.AllUppercase
            font.letterSpacing: 1
        }
        Text {
            visible: root.view.conversations.length === 0
            text: root.view.t.no_chats
            color: root.c.muted
            font.pixelSize: 12
        }
        ListView {
            width: parent.width
            height: parent.height - 190
            clip: true
            spacing: 2
            model: root.view.conversations
            delegate: Rectangle {
                property bool current: modelData.id === root.view.conversation_id
                width: ListView.view.width
                height: 50
                radius: 10
                color: current ? root.c.selected : (hover.containsMouse ? root.c.hover : "transparent")
                activeFocusOnTab: true
                Keys.onReturnPressed: root.chosen(modelData.id)
                Rectangle {
                    visible: parent.current
                    x: 0
                    anchors.verticalCenter: parent.verticalCenter
                    width: 3
                    height: 18
                    radius: 2
                    color: root.c.accent
                }
                Column {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.leftMargin: 14
                    anchors.rightMargin: 10
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2
                    Text {
                        width: parent.width
                        elide: Text.ElideRight
                        text: modelData.title !== "" ? modelData.title : modelData.updated_at.substring(0, 16).replace("T", " ")
                        color: root.c.text
                        font.pixelSize: 13
                        font.bold: current
                    }
                    Text {
                        width: parent.width
                        elide: Text.ElideRight
                        font.pixelSize: 11
                        color: current && root.view.status_kind === "busy" ? root.c.accentText : root.c.muted
                        text: current ? (root.view.run_active ? root.view.status_text : root.view.save_text)
                                      : (root.view.workspace_status[modelData.id] === undefined || root.view.workspace_status[modelData.id] === "none" ? root.view.t.no_project : "")
                    }
                }
                MouseArea {
                    id: hover
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.chosen(modelData.id)
                }
            }
        }
    }
}
