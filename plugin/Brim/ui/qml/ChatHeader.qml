import QtQuick 2.7

Rectangle {
    id: root
    property var view: ({})
    property var c: ({})
    property bool compact: false
    property string title: ""
    property bool closable: false
    property int epoch: 0
    property bool reduced: false
    signal menu()
    signal create()
    signal settings()
    signal exportRequested()
    signal modeChosen(string mode)
    signal close()

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
        Item {
            width: 14
            height: 14
            anchors.verticalCenter: parent.verticalCenter
            Spinner {
                anchors.fill: parent
                visible: root.view.status_kind === "busy"
                running: visible
                color: root.c.accent
                track: Qt.rgba(0.5, 0.5, 0.5, 0.25)
            }
            Rectangle {
                visible: root.view.status_kind !== "busy"
                anchors.centerIn: parent
                width: 8
                height: 8
                radius: 4
                color: root.view.status_kind === "error" ? root.c.danger : (root.view.status_kind === "ok" ? root.c.ok : root.c.accent)
            }
        }
        Column {
            anchors.verticalCenter: parent.verticalCenter
            width: Math.max(40, root.width - actions.width - 64 - (root.compact ? 42 : 0))
            ScrambleText {
                width: parent.width
                elide: Text.ElideRight
                source: root.title !== "" ? root.title : root.view.t.new_chat
                epoch: root.epoch
                reduced: root.reduced
                color: root.c.text
                font.pixelSize: 14
                font.bold: true
            }
            ScrambleText {
                width: parent.width
                elide: Text.ElideRight
                source: root.view.status_text + (root.view.save_text !== "" ? "  ·  " + root.view.save_text : "")
                epoch: root.epoch
                reduced: root.reduced
                color: root.view.status_kind === "error" ? root.c.danger : root.c.muted
                font.pixelSize: 11
            }
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
            ScrambleText {
                id: autoLabel
                x: 11
                anchors.verticalCenter: parent.verticalCenter
                source: root.view.t.mode_auto
                epoch: root.epoch
                reduced: root.reduced
                font.pixelSize: 12
                font.bold: root.view.mode === "auto"
                color: root.view.mode === "auto" ? root.c.actionText : root.c.text
            }
            ScrambleText {
                id: askLabel
                x: autoLabel.implicitWidth + 31
                anchors.verticalCenter: parent.verticalCenter
                source: root.view.t.mode_ask
                epoch: root.epoch
                reduced: root.reduced
                font.pixelSize: 12
                font.bold: root.view.mode === "ask"
                color: root.view.mode === "ask" ? root.c.actionText : root.c.text
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
            glyph: "export"
            palette_: root.c
            enabledButton: root.view.entries.length > 0 && !root.view.run_active && !root.view.exporting
            onClicked: root.exportRequested()
            HintBubble {
                shown: parent.hovered
                text: root.view.t.export_hint
                c: root.c
            }
        }
        IconButton {
            glyph: "gear"
            palette_: root.c
            onClicked: root.settings()
        }
        IconButton {
            visible: root.closable
            glyph: "close"
            palette_: root.c
            onClicked: root.close()
        }
    }
}
