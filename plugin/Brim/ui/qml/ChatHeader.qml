import QtQuick 2.7

Rectangle {
    id: root
    property var view: ({})
    property var c: ({})
    property bool compact: false
    property string title: ""
    signal menu()
    signal create()
    signal settings()
    signal modeChosen(string mode)

    height: 52
    color: c.bg

    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: root.c.line
    }

    Row {
        anchors.left: parent.left
        anchors.leftMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        spacing: 8
        IconButton {
            visible: root.compact
            glyph: "menu"
            palette_: root.c
            onClicked: root.menu()
        }
        Rectangle {
            width: 8
            height: 8
            radius: 4
            anchors.verticalCenter: parent.verticalCenter
            color: root.view.connection === "connected" ? root.c.ok : root.c.danger
        }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            width: Math.max(40, root.width - actions.width - 64 - (root.compact ? 42 : 0))
            elide: Text.ElideRight
            text: root.title !== "" ? root.title : (root.view.connection === "connected" ? root.view.t.connected : root.view.t.disconnected)
            color: root.c.text
            font.pixelSize: 14
            font.bold: true
        }
    }

    Row {
        id: actions
        anchors.right: parent.right
        anchors.rightMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        spacing: 6

        Rectangle {
            id: segmented
            width: autoLabel.implicitWidth + askLabel.implicitWidth + 40
            height: 30
            radius: 15
            color: root.c.selected
            anchors.verticalCenter: parent.verticalCenter

            Rectangle {
                x: root.view.mode === "auto" ? 2 : autoLabel.implicitWidth + 22
                y: 2
                width: (root.view.mode === "auto" ? autoLabel.implicitWidth : askLabel.implicitWidth) + 18
                height: 26
                radius: 13
                color: root.c.accent
                Behavior on x { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
                Behavior on width { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
            }
            Text {
                id: autoLabel
                x: 11
                anchors.verticalCenter: parent.verticalCenter
                text: root.view.t.mode_auto
                font.pixelSize: 12
                font.bold: root.view.mode === "auto"
                color: root.view.mode === "auto" ? "#12130f" : root.c.text
            }
            Text {
                id: askLabel
                x: autoLabel.implicitWidth + 31
                anchors.verticalCenter: parent.verticalCenter
                text: root.view.t.mode_ask
                font.pixelSize: 12
                font.bold: root.view.mode === "ask"
                color: root.view.mode === "ask" ? "#12130f" : root.c.text
            }
            MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.modeChosen(mouse.x < autoLabel.implicitWidth + 20 ? "auto" : "ask")
                HintBubble {
                    shown: parent.containsMouse
                    text: root.view.mode === "auto" ? root.view.t.mode_auto_hint : root.view.t.mode_ask_hint
                    c: root.c
                }
            }
        }
        IconButton {
            visible: root.compact
            glyph: "plus"
            palette_: root.c
            onClicked: root.create()
        }
        IconButton {
            glyph: "gear"
            palette_: root.c
            onClicked: root.settings()
        }
    }
}
