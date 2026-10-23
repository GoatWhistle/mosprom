import QtQuick 2.7

Rectangle {
    id: root
    property var view: ({})
    property var c: ({})
    property string language: view.language
    property string theme: view.theme
    signal closed()
    signal applied(string backend, string llmUrl, string model, string key, string language, string theme)
    signal checkRequested()

    color: c.bg

    MouseArea {
        anchors.fill: parent
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: 24
        contentHeight: column.height
        clip: true

        Column {
            id: column
            width: Math.min(parent.width, 520)
            spacing: 14

            Text {
                text: root.view.t.settings
                color: root.c.text
                font.pixelSize: 20
                font.bold: true
            }
            FieldInput {
                id: backend
                width: parent.width
                c: root.c
                label: root.view.t.backend_url
                initial: root.view.settings.backend_url
            }
            FieldInput {
                id: llmUrl
                width: parent.width
                c: root.c
                label: root.view.t.llm_url
                initial: root.view.settings.llm_base_url
                hint: "https://"
            }
            FieldInput {
                id: model
                width: parent.width
                c: root.c
                label: root.view.t.llm_model
                initial: root.view.settings.llm_model
            }
            FieldInput {
                id: key
                width: parent.width
                c: root.c
                secret: true
                label: root.view.t.llm_key
                hint: root.view.settings.llm_key_saved ? root.view.t.llm_key_saved : ""
            }
            Row {
                spacing: 8
                Text {
                    text: root.view.t.language
                    color: root.c.muted
                    font.pixelSize: 12
                    anchors.verticalCenter: parent.verticalCenter
                }
                BrimButton {
                    text: "RU"
                    primary: root.language === "ru"
                    palette_: root.c
                    onClicked: root.language = "ru"
                }
                BrimButton {
                    text: "EN"
                    primary: root.language === "en"
                    palette_: root.c
                    onClicked: root.language = "en"
                }
            }
            Row {
                spacing: 8
                Text {
                    text: root.view.t.theme
                    color: root.c.muted
                    font.pixelSize: 12
                    anchors.verticalCenter: parent.verticalCenter
                }
                BrimButton {
                    text: root.view.t.theme_dark
                    primary: root.theme === "dark"
                    palette_: root.c
                    onClicked: root.theme = "dark"
                }
                BrimButton {
                    text: root.view.t.theme_light
                    primary: root.theme === "light"
                    palette_: root.c
                    onClicked: root.theme = "light"
                }
            }
            Text {
                visible: root.view.mcp_port !== null && root.view.mcp_port !== undefined
                text: root.view.t.port_note + " " + root.view.mcp_port
                color: root.c.muted
                font.pixelSize: 12
            }
            Text {
                width: parent.width
                visible: !!root.view.settings_notice
                wrapMode: Text.Wrap
                text: root.view.settings_notice || ""
                color: root.c.accentText
                font.pixelSize: 12
            }
            Row {
                spacing: 8
                BrimButton {
                    text: root.view.t.save
                    primary: true
                    palette_: root.c
                    onClicked: root.applied(backend.value, llmUrl.value, model.value, key.value, root.language, root.theme)
                }
                BrimButton {
                    text: root.view.t.check
                    palette_: root.c
                    onClicked: root.checkRequested()
                }
                BrimButton {
                    text: root.view.t.close
                    palette_: root.c
                    onClicked: root.closed()
                }
            }
        }
    }
}
