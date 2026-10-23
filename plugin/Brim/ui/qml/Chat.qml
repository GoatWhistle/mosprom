import QtQuick 2.7
import QtQuick.Window 2.2
import QtQuick.Dialogs 1.2

Window {
    id: window
    width: 980
    height: 720
    minimumWidth: 400
    minimumHeight: 480
    title: "Brim"
    visible: false
    color: c.bg

    property var view: brim.view
    property bool settingsOpen: false
    property bool drawerOpen: false
    property bool narrow: width < 760
    property var expandedGroups: ({})
    property int draftRev: view.draft_rev
    onDraftRevChanged: composer.text = view.draft
    property string currentTitle: {
        var list = view.conversations
        for (var i = 0; i < list.length; i++) {
            if (list[i].id === view.conversation_id)
                return list[i].title
        }
        return ""
    }
    property bool dark: view.theme !== "light"
    property var c: dark ? {
        bg: "#12130f", panel: "#191a15", selected: "#22231d", hover: "#1d1e18", userBg: "#3a2a1c", userText: "#fbeee3", line: "#3c3c38", text: "#e4dfda",
        muted: "#9b968f", accent: "#ff8a3d", accentHover: "#ffa565", accentText: "#ff8a3d",
        danger: "#ff7a6b", ok: "#7fcf8a"
    } : {
        bg: "#f6f5f2", panel: "#ffffff", selected: "#ecebe7", hover: "#f1f0ec", userBg: "#ffe7d4", userText: "#2a1606", line: "#d8d4cd", text: "#12130f",
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
        brim.send(composer.text)
        timeline.jumpToEnd()
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

    ProjectList {
        id: sidebar
        width: window.narrow ? 0 : 248
        visible: width > 0
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        view: window.view
        c: window.c
        onChosen: brim.openChat(id)
        onCreate: brim.newChat()
        onCreateFromScene: brim.newChatFromScene()
    }

    Rectangle {
        visible: !window.narrow
        anchors.left: sidebar.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 1
        color: c.line
    }

    Item {
        id: main
        anchors.left: sidebar.right
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.leftMargin: window.narrow ? 0 : 1

        Rectangle {
            anchors.fill: parent
            color: c.bg
        }

        ChatHeader {
            id: header
            width: parent.width
            view: window.view
            c: window.c
            compact: window.narrow
            title: window.currentTitle
            onMenu: window.drawerOpen = true
            onCreate: brim.newChat()
            onSettings: window.settingsOpen = true
            onModeChosen: brim.setMode(mode)
        }

        Column {
            anchors.centerIn: parent
            spacing: 8
            visible: view.entries.length === 0
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 44
                height: 44
                radius: 22
                color: c.accent
                opacity: 0.9
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: view.t.empty_title
                color: c.text
                font.pixelSize: 18
                font.bold: true
            }
            Text {
                width: Math.min(420, main.width - 48)
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
            anchors.topMargin: 12
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: status.top
            anchors.leftMargin: 20
            anchors.rightMargin: 20
            clip: true
            spacing: 12
            model: view.entries
            property bool followEnd: true
            property bool unread: false
            function jumpToEnd() {
                positionViewAtEnd()
                followEnd = true
                unread = false
            }
            onMovementEnded: {
                followEnd = atYEnd
                if (atYEnd)
                    unread = false
            }
            onCountChanged: {
                if (followEnd)
                    positionViewAtEnd()
                else
                    unread = true
            }
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
                    case "tool_group":
                        return toolGroup
                    case "result":
                        return resultCard
                    default:
                        return errorRow
                    }
                }
            }
        }

        BrimButton {
            visible: timeline.unread
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: status.top
            anchors.bottomMargin: 8
            text: "↓  " + view.t.new_messages
            primary: true
            palette_: c
            onClicked: timeline.jumpToEnd()
        }

        Component {
            id: bubble
            MessageBubble {
                t: view.t
                c: window.c
            }
        }

        Component {
            id: questionCard
            Rectangle {
                property var entry: ({"questions": []})
                width: parent ? parent.width : 300
                height: questionColumn.height + 28
                radius: 14
                color: c.panel
                border.width: 2
                border.color: c.accent
                Column {
                    id: questionColumn
                    x: 16
                    y: 14
                    width: parent.width - 32
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
                onDecide: brim.confirm(decision, composer.text)
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
            id: toolGroup
            ToolGroup {
                t: view.t
                c: window.c
                expanded: !!window.expandedGroups[entry.key]
                onToggled: {
                    var copy = {}
                    for (var k in window.expandedGroups)
                        copy[k] = window.expandedGroups[k]
                    copy[entry.key] = value
                    window.expandedGroups = copy
                }
            }
        }

        Component {
            id: resultCard
            ResultCard {
                property var entry: ({})
                width: parent ? parent.width : 300
                result: entry.result || ({})
                stale: view.result_stale
                t: view.t
                c: window.c
                onSave: {
                    saveDialog.kind = kind
                    saveDialog.open()
                }
            }
        }

        Component {
            id: errorRow
            Rectangle {
                property var entry: ({})
                width: parent ? parent.width : 300
                height: errorText.height + 24
                radius: 12
                color: Qt.rgba(1, 0.45, 0.4, 0.08)
                border.width: 1
                border.color: c.danger
                SelectableText {
                    id: errorText
                    x: 14
                    y: 12
                    width: parent.width - 28
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

            Rectangle {
                visible: view.progress !== null && view.progress !== undefined
                width: parent.width
                height: 4
                radius: 2
                color: c.selected
                Rectangle {
                    width: parent.width * Math.max(0, Math.min(1, (view.progress || {}).fraction || 0))
                    height: parent.height
                    radius: 2
                    color: c.accent
                }
            }
            Text {
                visible: view.progress !== null && view.progress !== undefined && !!(view.progress || {}).stage
                text: (view.progress || {}).stage || ""
                color: c.muted
                font.pixelSize: 12
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
            Flow {
                width: parent.width
                spacing: 8
                visible: view.can_retry_switch || view.workspace_blocked
                BrimButton {
                    visible: view.can_retry_switch
                    text: view.t.retry
                    primary: true
                    palette_: c
                    onClicked: brim.retrySwitch()
                }
                BrimButton {
                    visible: view.workspace_blocked
                    text: view.t.recover
                    primary: true
                    palette_: c
                    enabledButton: view.switching === null
                    onClicked: brim.recoverWorkspace()
                }
            }
        }

        Composer {
            id: composer
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            anchors.bottomMargin: 10
            view: window.view
            c: window.c
            onSend: window.sendCurrent()
            onAttach: attachDialog.open()
            onStop: brim.stop()
            onDetach: brim.removeAttachment(index)
            onTextChanged: brim.setDraft(text)
        }
    }

    Rectangle {
        anchors.fill: parent
        visible: window.narrow && opacity > 0
        opacity: window.drawerOpen ? 1 : 0
        color: "#99000000"
        Behavior on opacity { NumberAnimation { duration: 140 } }
        MouseArea {
            anchors.fill: parent
            enabled: window.drawerOpen
            onClicked: window.drawerOpen = false
        }
        ProjectList {
            x: window.drawerOpen ? 0 : -width
            width: Math.min(280, parent.width - 48)
            height: parent.height
            view: window.view
            c: window.c
            Behavior on x { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
            onChosen: {
                window.drawerOpen = false
                brim.openChat(id)
            }
            onCreate: {
                window.drawerOpen = false
                brim.newChat()
            }
            onCreateFromScene: {
                window.drawerOpen = false
                brim.newChatFromScene()
            }
            MouseArea {
                z: -1
                anchors.fill: parent
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        visible: view.switching !== null || view.switch_prompt
        color: "#b3000000"
        MouseArea {
            anchors.fill: parent
        }
        Rectangle {
            anchors.centerIn: parent
            width: Math.min(360, parent.width - 48)
            height: dialogColumn.height + 40
            radius: 16
            color: c.panel
            border.width: 1
            border.color: c.line
            Column {
                id: dialogColumn
                x: 20
                y: 20
                width: parent.width - 40
                spacing: 12
                Text {
                    width: parent.width
                    wrapMode: Text.Wrap
                    text: view.switching !== null ? view.status_text : view.t.switch_busy_title
                    color: c.text
                    font.pixelSize: 15
                    font.bold: true
                }
                Text {
                    visible: view.switch_prompt
                    width: parent.width
                    wrapMode: Text.Wrap
                    text: view.t.switch_busy_body
                    color: c.muted
                    font.pixelSize: 13
                }
                Rectangle {
                    visible: view.switching !== null
                    width: parent.width
                    height: 4
                    radius: 2
                    color: c.selected
                    clip: true
                    Rectangle {
                        width: parent.width * 0.35
                        height: parent.height
                        radius: 2
                        color: c.accent
                        SequentialAnimation on x {
                            running: view.switching !== null
                            loops: Animation.Infinite
                            NumberAnimation { from: 0; to: dialogColumn.width * 0.65; duration: 900; easing.type: Easing.InOutQuad }
                            NumberAnimation { from: dialogColumn.width * 0.65; to: 0; duration: 900; easing.type: Easing.InOutQuad }
                        }
                    }
                }
                Flow {
                    visible: view.switch_prompt
                    width: parent.width
                    spacing: 8
                    BrimButton {
                        text: view.t.switch_stop
                        primary: true
                        palette_: c
                        onClicked: brim.stopAndSwitch()
                    }
                    BrimButton {
                        text: view.t.switch_wait
                        palette_: c
                        onClicked: brim.cancelSwitch()
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
