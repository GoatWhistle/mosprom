import QtQuick 2.7

Rectangle {
    id: root
    property var view: ({})
    property var c: ({})
    signal chosen(string id)
    signal create()

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
            height: parent.height - 130
            clip: true
            spacing: 2
            model: root.view.conversations
            delegate: Rectangle {
                property bool current: modelData.id === root.view.conversation_id
                width: ListView.view.width
                height: 38
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
                Text {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 10
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                    text: modelData.title !== "" ? modelData.title : modelData.updated_at.substring(0, 16).replace("T", " ")
                    color: root.c.text
                    font.pixelSize: 13
                    font.bold: parent.current
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
