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
    property bool wantDark: view.theme !== "light"
    property bool dark: true
    property string language: view.language
    property int langEpoch: 0
    onLanguageChanged: langEpoch++
    onWantDarkChanged: sweep.run(wantDark ? theme.darkPalette.bg : theme.lightPalette.bg, function () { panel.dark = panel.wantDark })
    property var c: dark ? theme.darkPalette : theme.lightPalette

    Theme {
        id: theme
    }

    BrimFonts {
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
    property string syncedConversation: "\u0000"

    onViewChanged: syncEntries()
    Component.onCompleted: {
        dark = wantDark
        syncEntries()
    }

    function syncEntries() {
        var list = view.entries || []
        var switched = view.conversation_id !== syncedConversation
        if (switched) {
            syncedConversation = view.conversation_id
            entryModel.clear()
        }
        var keep = 0
        while (keep < list.length && keep < entryModel.count && entryModel.get(keep).key === list[keep].key)
            keep++
        for (var i = 0; i < keep; i++) {
            var payload = JSON.stringify(list[i])
            if (entryModel.get(i).payload !== payload) {
                entryModel.setProperty(i, "kind", list[i].kind)
                entryModel.setProperty(i, "payload", payload)
            }
        }
        if (entryModel.count > keep)
            entryModel.remove(keep, entryModel.count - keep)
        for (var j = keep; j < list.length; j++)
            entryModel.append({ key: list[j].key, kind: list[j].kind, payload: JSON.stringify(list[j]) })
        if (switched)
            timeline.jumpToEnd()
    }

    ListModel {
        id: entryModel
    }

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
        folder: shortcuts.home
        nameFilters: ["Models, images and documents (*.stl *.obj *.3mf *.jpg *.jpeg *.png *.docx *.xlsx *.csv *.tsv *.txt *.md *.json *.pdf)", "All files (*)"]
        onAccepted: {
            for (var i = 0; i < fileUrls.length; i++)
                brim.attach(fileUrls[i].toString())
        }
    }

    FileDialog {
        id: exportDialog
        title: view.t.export_choose
        selectFolder: true
        folder: brim.exportRoot !== "" ? brim.exportRoot : shortcuts.documents
        onAccepted: brim.exportChat(fileUrl.toString())
    }

    TimelineCapture {
        id: capture
        list: timeline
        frame: main
        onFinished: brim.captureDone(pages, error)
    }

    Connections {
        target: brim
        onCaptureRequested: capture.start(path)
    }

    ProjectList {
        id: sidebar
        width: panel.narrow ? 0 : 248
        visible: width > 0
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        view: panel.view
        c: panel.c
        dark: panel.dark
        epoch: panel.langEpoch
        reduced: theme.reducedMotion
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
            epoch: panel.langEpoch
            reduced: theme.reducedMotion
            compact: panel.narrow
            title: panel.currentTitle
            onMenu: panel.drawerOpen = true
            onCreate: brim.newChat()
            onSettings: panel.settingsOpen = true
            onModeChosen: brim.setMode(mode)
            onExportRequested: exportDialog.open()
            closable: panel.closable
            onClose: panel.closeRequested()
        }

        Column {
            anchors.centerIn: parent
            spacing: 14
            visible: view.entries.length === 0
            BrandMark {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 64
                height: 64
                base: c.text
                accent: c.accent
                intro: true
                reduced: theme.reducedMotion
            }
            ScrambleText {
                anchors.horizontalCenter: parent.horizontalCenter
                source: view.t.empty_title
                epoch: panel.langEpoch
                reduced: theme.reducedMotion
                color: c.text
                font.pixelSize: 20
                font.weight: Font.Medium
            }
            BrimText {
                width: Math.min(420, main.width - 48)
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                text: view.t.empty_body
                color: c.muted
                font.pixelSize: 13
            }
        }

        Flickable {
            id: timeline
            anchors.top: header.bottom
            anchors.topMargin: 12
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: status.top
            anchors.leftMargin: 20
            anchors.rightMargin: 20
            clip: true
            flickableDirection: Flickable.VerticalFlick
            contentWidth: width
            contentHeight: rows.height
            property alias count: rowRepeater.count
            property bool followEnd: true
            property bool unread: false
            property bool pinning: false
            property int seenCount: 0
            function positionViewAtEnd() {
                pinning = true
                contentY = originY + Math.max(0, contentHeight - height)
                pinning = false
            }
            function positionViewAtBeginning() {
                pinning = true
                contentY = originY
                pinning = false
            }
            function jumpToEnd() {
                followEnd = true
                unread = false
                positionViewAtEnd()
            }
            onContentYChanged: {
                if (pinning)
                    return
                followEnd = atYEnd
                if (atYEnd)
                    unread = false
            }
            onContentHeightChanged: {
                if (followEnd)
                    positionViewAtEnd()
            }
            onHeightChanged: {
                if (followEnd)
                    positionViewAtEnd()
            }
            onCountChanged: {
                if (!followEnd && count > seenCount)
                    unread = true
                seenCount = count
            }

            Column {
                id: rows
                width: timeline.width
                spacing: 12

                Repeater {
                    id: rowRepeater
                    model: entryModel
                    delegate: Loader {
                        id: slot
                        width: timeline.width
                        property var entry: JSON.parse(payload)
                        transform: Translate { id: rise }
                        Component.onCompleted: {
                            if (!panel.isFresh(key))
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
                        onLoaded: item.entry = Qt.binding(function() { return slot.entry })
                        sourceComponent: {
                            switch (kind) {
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
            }
        }

        BrimButton {
            visible: timeline.unread && !capture.active
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
                radius: 0
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
            BrimText {
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
                BrimText {
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
                    enabledButton: !view.switching
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
            onSkillChosen: brim.setSkill(name)
            onTextChanged: brim.setDraft(text)
        }

        DropArea {
            id: fileDrop
            anchors.fill: parent
            onEntered: drag.accepted = drag.hasUrls && !view.busy
            onDropped: {
                if (!drop.hasUrls)
                    return
                for (var i = 0; i < drop.urls.length; i++)
                    brim.attach(drop.urls[i].toString())
                drop.acceptProposedAction()
                composer.focusInput()
            }
        }

        Rectangle {
            anchors.fill: parent
            anchors.margins: 8
            visible: fileDrop.containsDrag
            radius: 0
            color: Qt.rgba(1, 0.54, 0.24, 0.10)
            border.width: 2
            border.color: c.accent
            BrimText {
                anchors.centerIn: parent
                width: parent.width - 48
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                text: view.t.drop_files
                color: c.accentText
                font.pixelSize: 15
                font.bold: true
            }
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
            dark: panel.dark
            epoch: panel.langEpoch
            reduced: theme.reducedMotion
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

    LayerSweep {
        id: sweep
        anchors.fill: parent
        reduced: theme.reducedMotion
    }
}
