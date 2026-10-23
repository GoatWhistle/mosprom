import QtQuick 2.7
import QtQuick.Dialogs 1.2

Item {
    id: panel
    property bool closable: false
    signal closeRequested()

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

    Theme {
        id: theme
    }

    property string seenConversation: "\u0000"
    property var seenKeys: ({})

    function isFresh(key) {
        if (view.conversation_id !== seenConversation) {
            seenConversation = view.conversation_id
            var keys = {}
            var list = view.entries
            for (var i = 0; i < list.length; i++)
                keys[list[i].key] = true
            seenKeys = keys
            return false
        }
        if (seenKeys[key])
            return false
        seenKeys[key] = true
        return true
    }

    property var announced: ({})

    function once(key) {
        if (announced[key])
            return false
        announced[key] = true
        return true
    }

    function openSettings() {
        settingsOpen = true
    }

    function sendCurrent() {
        brim.send(composer.text)
        timeline.jumpToEnd()
    }

    Rectangle {
        anchors.fill: parent
        color: c.bg
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

    ProjectList {
        id: sidebar
        width: panel.narrow ? 0 : 248
        visible: width > 0
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        view: panel.view
        c: panel.c
        onChosen: brim.openChat(id)
        onCreate: brim.newChat()
        onCreateFromScene: brim.newChatFromScene()
    }

    Rectangle {
        visible: !panel.narrow
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
        anchors.leftMargin: panel.narrow ? 0 : 1

        Rectangle {
            anchors.fill: parent
            color: c.bg
        }

        ChatHeader {
            id: header
            width: parent.width
            view: panel.view
            c: panel.c
            compact: panel.narrow
            title: panel.currentTitle
            onMenu: panel.drawerOpen = true
            onCreate: brim.newChat()
            onSettings: panel.settingsOpen = true
            onModeChosen: brim.setMode(mode)
            closable: panel.closable
            onClose: panel.closeRequested()
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
            cacheBuffer: 1000000
            model: view.entries
            property bool followEnd: true
            property bool unread: false
            function jumpToEnd() {
                positionViewAtEnd()
                followEnd = true
                unread = false
            }
            function followToEnd() {
                if (!followEnd)
                    return
                settle.left = 20
                settle.lastY = -1
                settle.restart()
            }
            Timer {
                id: settle
                interval: 16
                repeat: true
                property int left: 0
                property real lastY: -1
                onTriggered: {
                    timeline.positionViewAtEnd()
                    left -= 1
                    if (timeline.contentY === lastY || left <= 0)
                        stop()
                    lastY = timeline.contentY
                }
            }
            onMovementStarted: settle.stop()
            onMovementEnded: {
                followEnd = atYEnd
                if (atYEnd)
                    unread = false
            }
            onCountChanged: {
                if (followEnd)
                    followToEnd()
                else
                    unread = true
            }
            onModelChanged: followToEnd()
            onHeightChanged: followToEnd()

            delegate: Loader {
                id: slot
                width: ListView.view.width
                property var entry: modelData
                transform: Translate { id: rise }
                Component.onCompleted: {
                    if (!panel.isFresh(modelData.key))
                        return
                    opacity = 0
                    rise.y = 6
                    appear.start()
                }
                ParallelAnimation {
                    id: appear
                    NumberAnimation { target: slot; property: "opacity"; to: 1; duration: theme.durBase; easing.type: theme.easeOut }
                    NumberAnimation { target: rise; property: "y"; to: 0; duration: theme.durBase; easing.type: theme.easeOut }
                }
                onHeightChanged: {
                    if (index === timeline.count - 1)
                        timeline.followToEnd()
                }
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
                c: panel.c
            }
        }

        Component {
            id: questionCard
            QuestionCard {
                t: view.t
                c: panel.c
                active: !!view.question && view.question.call_id === entry.call_id && !view.busy
                onPicked: {
                    var line = (entry.questions.length > 1 ? (index + 1) + ". " : "") + option
                    composer.text = composer.text === "" ? line : composer.text + "\n" + line
                    composer.focusInput()
                }
            }
        }

        Component {
            id: confirmCard
            ConfirmCard {
                t: view.t
                c: panel.c
                active: !!view.confirmation && view.confirmation.call_id === entry.call_id && !view.busy
                onDecide: brim.confirm(decision, composer.text)
                onEntryChanged: {
                    if (entry && entry.call_id && panel.once("confirm-" + entry.call_id))
                        announce()
                }
            }
        }

        Component {
            id: toolRow
            ToolRow {
                t: view.t
                c: panel.c
            }
        }

        Component {
            id: toolGroup
            ToolGroup {
                t: view.t
                c: panel.c
                expanded: !!panel.expandedGroups[entry.key]
                onToggled: {
                    var copy = {}
                    for (var k in panel.expandedGroups)
                        copy[k] = panel.expandedGroups[k]
                    copy[entry.key] = value
                    panel.expandedGroups = copy
                }
            }
        }

        Component {
            id: resultCard
            ResultCard {
                property var entry: ({})
                width: parent ? parent.width : 300
                result: entry.result || ({})
                t: view.t
                c: panel.c
                onOpen: brim.openPath(path)
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

            ActivityBar {
                width: parent.width
                activity: view.activity || null
                progress: view.progress || null
                t: view.t
                c: panel.c
                theme: theme
                onStop: brim.stop()
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
            Column {
                width: parent.width
                spacing: 6
                visible: view.switch_prompt
                Text {
                    width: parent.width
                    wrapMode: Text.Wrap
                    text: view.t.switch_busy_title + ". " + view.t.switch_busy_body
                    color: c.text
                    font.pixelSize: 12
                }
                Flow {
                    width: parent.width
                    spacing: 8
                    BrimButton {
                        text: view.t.switch_wait
                        palette_: c
                        onClicked: brim.cancelSwitch()
                    }
                    BrimButton {
                        text: view.t.switch_stop
                        danger: true
                        palette_: c
                        onClicked: brim.stopAndSwitch()
                    }
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
            view: panel.view
            c: panel.c
            onSend: panel.sendCurrent()
            onAttach: attachDialog.open()
            onStop: brim.stop()
            onDetach: brim.removeAttachment(index)
            onTextChanged: brim.setDraft(text)
        }
    }

    Rectangle {
        anchors.fill: parent
        visible: panel.narrow && opacity > 0
        opacity: panel.drawerOpen ? 1 : 0
        color: "#99000000"
        Behavior on opacity { NumberAnimation { duration: 140 } }
        MouseArea {
            anchors.fill: parent
            enabled: panel.drawerOpen
            onClicked: panel.drawerOpen = false
        }
        ProjectList {
            x: panel.drawerOpen ? 0 : -width
            width: Math.min(280, parent.width - 48)
            height: parent.height
            view: panel.view
            c: panel.c
            Behavior on x { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
            onChosen: {
                panel.drawerOpen = false
                brim.openChat(id)
            }
            onCreate: {
                panel.drawerOpen = false
                brim.newChat()
            }
            onCreateFromScene: {
                panel.drawerOpen = false
                brim.newChatFromScene()
            }
            MouseArea {
                z: -1
                anchors.fill: parent
            }
        }
    }

    SettingsPanel {
        anchors.fill: parent
        visible: panel.settingsOpen
        view: panel.view
        c: panel.c
        onClosed: panel.settingsOpen = false
        onApplied: {
            if (brim.applySettings(llmUrl, model, key, language, theme))
                panel.settingsOpen = false
        }
        onCheckRequested: brim.checkConnection()
    }
}
