import QtQuick 2.7
import QtQuick.Window 2.2
import QtQuick.Dialogs 1.2

Window {
    id: window
    width: 980
    height: 720
    minimumWidth: 640
    minimumHeight: 480
    title: "Brim"
    visible: false
    color: c.bg

    property var view: brim.view
    property bool settingsOpen: false
    property bool dark: view.theme !== "light"
    property var c: dark ? {
        bg: "#12130f", panel: "#191a15", selected: "#22231d", line: "#3c3c38", text: "#e4dfda",
        muted: "#9b968f", accent: "#ff8a3d", accentHover: "#ffa565", accentText: "#ff8a3d",
        danger: "#ff7a6b", ok: "#7fcf8a"
    } : {
        bg: "#f6f5f2", panel: "#ffffff", selected: "#ecebe7", line: "#d8d4cd", text: "#12130f",
        muted: "#615c56", accent: "#ff8a3d", accentHover: "#f2752a", accentText: "#b83f0a",
        danger: "#b3261e", ok: "#2e7d32"
    }

    function present() {
        visible = true
        raise()
        requestActivate()
    }

    function openSettings() {
        settingsOpen = true
        present()
    }

    function sendCurrent() {
        brim.send(input.text)
        input.text = ""
    }

    onClosing: {
        settingsOpen = false
    }

    FileDialog {
        id: attachDialog
        title: view.t.attach
        selectMultiple: true
        nameFilters: ["Models and images (*.stl *.obj *.3mf *.jpg *.jpeg *.png)"]
        onAccepted: {
            for (var i = 0; i < fileUrls.length; i++)
                brim.attach(fileUrls[i].toString())
        }
    }

    FileDialog {
        id: saveDialog
        property string kind: "gcode"
        title: kind === "gcode" ? view.t.save_gcode : view.t.save_3mf
        selectExisting: false
        onAccepted: brim.saveArtifact(kind, fileUrl.toString())
    }

    Rectangle {
        id: sidebar
        width: window.width < 820 ? 0 : 230
        visible: width > 0
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        color: c.panel

        Column {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 10

            Text {
                text: "Brim"
                color: c.accent
                font.pixelSize: 22
                font.bold: true
            }
            BrimButton {
                width: parent.width
                text: view.t.new_chat
                primary: true
                palette_: c
                onClicked: brim.newChat()
            }
            Text {
                text: view.t.chats
                color: c.muted
                font.pixelSize: 12
            }
            Text {
                visible: view.conversations.length === 0
                text: view.t.no_chats
                color: c.muted
                font.pixelSize: 12
            }
            ListView {
                width: parent.width
                height: parent.height - 120
                clip: true
                spacing: 4
                model: view.conversations
                delegate: Rectangle {
                    width: ListView.view.width
                    height: 36
                    radius: 6
                    color: modelData.id === view.conversation_id ? c.selected : "transparent"
                    activeFocusOnTab: true
                    Keys.onReturnPressed: brim.openChat(modelData.id)
                    Text {
                        anchors.fill: parent
                        anchors.leftMargin: 10
                        anchors.rightMargin: 10
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                        text: modelData.title !== "" ? modelData.title : modelData.updated_at.substring(0, 16).replace("T", " ")
                        color: c.text
                        font.pixelSize: 13
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: brim.openChat(modelData.id)
                    }
                }
            }
        }
    }

    Item {
        id: main
        anchors.left: sidebar.right
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom

        Rectangle {
            anchors.fill: parent
            color: c.bg
        }

        Rectangle {
            id: header
            width: parent.width
            height: 48
            color: c.bg
            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: c.line
            }
            Row {
                anchors.left: parent.left
                anchors.leftMargin: 16
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                Rectangle {
                    width: 8
                    height: 8
                    radius: 4
                    anchors.verticalCenter: parent.verticalCenter
                    color: view.connection === "connected" ? c.ok : c.danger
                }
                Text {
                    text: view.connection === "connected" ? view.t.connected : view.t.disconnected
                    color: c.muted
                    font.pixelSize: 12
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
            Row {
                anchors.right: parent.right
                anchors.rightMargin: 16
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                BrimButton {
                    text: view.t.mode_auto
                    primary: view.mode === "auto"
                    palette_: c
                    onClicked: brim.setMode("auto")
                }
                BrimButton {
                    text: view.t.mode_ask
                    primary: view.mode === "ask"
                    palette_: c
                    onClicked: brim.setMode("ask")
                }
                BrimButton {
                    text: view.t.settings
                    palette_: c
                    onClicked: window.settingsOpen = true
                }
            }
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: header.bottom
            anchors.topMargin: 6
            text: view.mode === "auto" ? view.t.mode_auto_hint : view.t.mode_ask_hint
            color: c.muted
            font.pixelSize: 11
        }

        Column {
            anchors.centerIn: parent
            spacing: 6
            visible: view.entries.length === 0
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: view.t.empty_title
                color: c.text
                font.pixelSize: 18
                font.bold: true
            }
            Text {
                width: main.width * 0.6
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                text: view.t.empty_body
                color: c.muted
                font.pixelSize: 13
            }
        }

        ListView {
            id: timeline
            anchors.top: header.bottom
            anchors.topMargin: 24
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: status.top
            anchors.leftMargin: 20
            anchors.rightMargin: 20
            clip: true
            spacing: 10
            model: view.entries
            property bool followEnd: true
            onMovementEnded: followEnd = atYEnd
            onCountChanged: if (followEnd) positionViewAtEnd()
            onContentHeightChanged: if (followEnd) positionViewAtEnd()

            delegate: Loader {
                id: slot
                width: ListView.view.width
                property var entry: modelData
                onLoaded: item.entry = Qt.binding(function() { return slot.entry })
                sourceComponent: {
                    switch (modelData.kind) {
                    case "user":
                    case "assistant":
                        return bubble
                    case "question":
                        return questionCard
                    case "confirmation":
                        return confirmCard
                    case "tool":
                        return toolRow
                    default:
                        return errorRow
                    }
                }
            }
        }

        Component {
            id: bubble
            Rectangle {
                property var entry: ({})
                property bool mine: entry.kind === "user"
                width: parent ? parent.width : 300
                height: bubbleColumn.height + 20
                radius: 8
                color: mine ? c.selected : c.panel
                border.width: 1
                border.color: c.line
                Column {
                    id: bubbleColumn
                    x: 14
                    y: 10
                    width: parent.width - 28
                    spacing: 4
                    Text {
                        text: mine ? view.t.you : view.t.agent
                        color: mine ? c.muted : c.accentText
                        font.pixelSize: 11
                        font.bold: true
                    }
                    SelectableText {
                        width: parent.width
                        text: entry.text
                        textColor: c.text
                    }
                    Repeater {
                        model: entry.attachments || []
                        delegate: Text {
                            text: "📎 " + modelData
                            color: c.muted
                            font.pixelSize: 12
                        }
                    }
                }
            }
        }

        Component {
            id: questionCard
            Rectangle {
                property var entry: ({"questions": []})
                width: parent ? parent.width : 300
                height: questionColumn.height + 24
                radius: 8
                color: c.panel
                border.width: 1
                border.color: c.accent
                Column {
                    id: questionColumn
                    x: 14
                    y: 12
                    width: parent.width - 28
                    spacing: 6
                    Text {
                        text: view.t.question
                        color: c.accentText
                        font.bold: true
                        font.pixelSize: 13
                    }
                    Repeater {
                        model: entry.questions
                        delegate: SelectableText {
                            width: questionColumn.width
                            text: (index + 1) + ". " + modelData
                            textColor: c.text
                        }
                    }
                    Text {
                        text: view.t.answer_hint
                        color: c.muted
                        font.pixelSize: 12
                    }
                }
            }
        }

        Component {
            id: confirmCard
            ConfirmCard {
                t: view.t
                c: window.c
                active: !!view.pending && view.pending.type === "confirmation" && view.pending.batch_id === entry.batch_id && !view.busy
                onDecide: brim.confirm(decision, input.text)
            }
        }

        Component {
            id: toolRow
            ToolRow {
                t: view.t
                c: window.c
            }
        }

        Component {
            id: errorRow
            Rectangle {
                property var entry: ({})
                width: parent ? parent.width : 300
                height: errorText.height + 20
                radius: 6
                color: c.panel
                border.width: 1
                border.color: c.danger
                SelectableText {
                    id: errorText
                    x: 12
                    y: 10
                    width: parent.width - 24
                    text: view.t.error + ": " + entry.text
                    textColor: c.danger
                }
            }
        }

        Column {
            id: status
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: composer.top
            anchors.leftMargin: 20
            anchors.rightMargin: 20
            anchors.bottomMargin: 8
            spacing: 8

            ResultCard {
                width: parent.width
                visible: view.result !== null && view.result !== undefined
                result: view.result || ({})
                t: view.t
                c: window.c
                onSave: {
                    saveDialog.kind = kind
                    saveDialog.open()
                }
            }
            Row {
                spacing: 10
                visible: view.run_state !== null && view.run_state !== undefined
                Text {
                    text: view.t["state_" + view.run_state] || ""
                    color: c.muted
                    font.pixelSize: 12
                    anchors.verticalCenter: parent.verticalCenter
                }
                Rectangle {
                    visible: view.progress !== null && view.progress !== undefined
                    width: 160
                    height: 6
                    radius: 3
                    color: c.selected
                    anchors.verticalCenter: parent.verticalCenter
                    Rectangle {
                        width: parent.width * Math.max(0, Math.min(1, (view.progress || {}).fraction || 0))
                        height: parent.height
                        radius: 3
                        color: c.accent
                    }
                }
                Text {
                    visible: view.progress !== null && view.progress !== undefined
                    text: (view.progress || {}).stage || ""
                    color: c.muted
                    font.pixelSize: 12
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
            Text {
                width: parent.width
                visible: !!view.notice
                wrapMode: Text.Wrap
                text: view.notice || ""
                color: c.accentText
                font.pixelSize: 12
                MouseArea {
                    anchors.fill: parent
                    onClicked: brim.dismissNotice()
                }
            }
        }

        Rectangle {
            id: composer
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 16
            height: Math.min(180, Math.max(88, input.contentHeight + 64 + (view.attachments.length > 0 ? 28 : 0)))
            radius: 8
            color: c.panel
            border.width: 1
            border.color: input.activeFocus ? c.accent : c.line

            Column {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 6

                Row {
                    spacing: 6
                    visible: view.attachments.length > 0
                    Repeater {
                        model: view.attachments
                        delegate: Rectangle {
                            height: 22
                            width: chipLabel.width + 40
                            radius: 11
                            color: c.selected
                            Text {
                                id: chipLabel
                                x: 10
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.name
                                color: c.text
                                font.pixelSize: 12
                            }
                            Text {
                                anchors.right: parent.right
                                anchors.rightMargin: 8
                                anchors.verticalCenter: parent.verticalCenter
                                text: "×"
                                color: c.muted
                                font.pixelSize: 14
                                MouseArea {
                                    anchors.fill: parent
                                    anchors.margins: -4
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: brim.removeAttachment(index)
                                }
                            }
                        }
                    }
                }

                Flickable {
                    width: parent.width
                    height: parent.height - 34 - (view.attachments.length > 0 ? 28 : 0)
                    contentHeight: input.contentHeight
                    clip: true
                    TextEdit {
                        id: input
                        width: parent.width
                        wrapMode: TextEdit.Wrap
                        selectByMouse: true
                        color: c.text
                        font.pixelSize: 14
                        selectionColor: c.accent
                        selectedTextColor: "#12130f"
                        activeFocusOnTab: true
                        focus: true
                        Keys.onPressed: {
                            if ((event.key === Qt.Key_Return || event.key === Qt.Key_Enter) && !(event.modifiers & Qt.ShiftModifier)) {
                                event.accepted = true
                                window.sendCurrent()
                            }
                        }
                        Text {
                            visible: input.text === ""
                            text: view.t.placeholder
                            color: c.muted
                            font.pixelSize: 13
                        }
                    }
                }

                Row {
                    spacing: 8
                    BrimButton {
                        text: view.t.attach
                        palette_: c
                        enabledButton: !view.busy
                        onClicked: attachDialog.open()
                    }
                    BrimButton {
                        text: view.t.send
                        primary: true
                        palette_: c
                        enabledButton: !view.busy
                        onClicked: window.sendCurrent()
                    }
                    BrimButton {
                        text: view.t.stop
                        danger: true
                        palette_: c
                        visible: view.run_active
                        onClicked: brim.stop()
                    }
                }
            }
        }
    }

    SettingsPanel {
        anchors.fill: parent
        visible: window.settingsOpen
        view: window.view
        c: window.c
        onClosed: window.settingsOpen = false
        onApplied: {
            if (brim.applySettings(backend, llmUrl, model, key, language, theme))
                window.settingsOpen = false
        }
        onCheckRequested: brim.checkBackend()
    }
}
