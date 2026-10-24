import QtQuick 2.7

Rectangle {
    id: root
    property var view: ({})
    property var c: ({})
    property bool dark: true
    property int epoch: 0
    property bool reduced: false
    signal chosen(string id)
    signal create()
    signal createFromScene()

    color: c.panel

    Column {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 12

        BrandLockup {
            markSize: 26
            dark: root.dark
            base: root.c.text
            accent: root.c.accent
            intro: true
            reduced: root.reduced
        }
        BrimButton {
            width: parent.width
            text: "+  " + root.view.t.new_chat
            primary: true
            epoch: root.epoch
            reduced: root.reduced
            palette_: root.c
            onClicked: root.create()
        }
        BrimButton {
            width: parent.width
            text: root.view.t.new_from_scene
            epoch: root.epoch
            reduced: root.reduced
            palette_: root.c
            enabledButton: !root.view.busy && !root.view.switching
            onClicked: root.createFromScene()
        }
        ScrambleText {
            source: root.view.t.chats
            epoch: root.epoch
            reduced: root.reduced
            color: root.c.muted
            font.pixelSize: 11
            font.bold: true
            font.capitalization: Font.AllUppercase
            font.letterSpacing: 1
        }
        BrimText {
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
                radius: 0
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
                    BrimText {
                        width: parent.width
                        elide: Text.ElideRight
                        text: modelData.title !== "" ? modelData.title : modelData.updated_at.substring(0, 16).replace("T", " ")
                        color: root.c.text
                        font.pixelSize: 13
                        font.bold: current
                    }
                    BrimText {
                        width: parent.width
                        elide: Text.ElideRight
                        font.pixelSize: 11
                        color: current && root.view.status_kind === "busy" ? root.c.accentText : root.c.muted
                        text: current ? (root.view.run_active ? root.view.status_text : root.view.save_text)
                                      : modelData.updated_at.substring(0, 16).replace("T", " ")
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
