import QtQuick 2.7

Rectangle {
    id: root
    property var view: ({})
    property var c: ({})
    property string language: view.language
    property string theme: view.theme
    signal closed()
    signal applied(string llmUrl, string model, string key, string language, string theme)
    signal checkRequested()

    color: c.bg

    function serverState(server) {
        var text = root.view.t["server_state_" + server.state] || server.state
        if (server.state === "ok")
            text += " · " + server.tools + " " + root.view.t.tools_count
        if (server.state === "error" && server.error)
            text += ": " + server.error
        return text
    }

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
            width: Math.min(parent.width, 560)
            spacing: 14

            BrimText {
                text: root.view.t.settings
                color: root.c.text
                font.pixelSize: 20
                font.bold: true
            }
            BrimText {
                text: root.view.t.llm_section
                color: root.c.text
                font.pixelSize: 14
                font.bold: true
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
            BrimText {
                text: root.view.t.interface_section
                color: root.c.text
                font.pixelSize: 14
                font.bold: true
            }
            Row {
                spacing: 8
                BrimText {
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
                BrimText {
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
            BrimText {
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
                    onClicked: root.applied(llmUrl.value, model.value, key.value, root.language, root.theme)
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
            Rectangle {
                width: parent.width
                height: 1
                color: root.c.line
            }
            BrimText {
                text: root.view.t.servers
                color: root.c.text
                font.pixelSize: 14
                font.bold: true
            }
            BrimText {
                width: parent.width
                wrapMode: Text.Wrap
                text: root.view.t.servers_hint
                color: root.c.muted
                font.pixelSize: 12
            }
            Repeater {
                model: root.view.servers || []
                delegate: Rectangle {
                    width: column.width
                    height: serverColumn.height + 20
                    radius: 0
                    color: root.c.panel
                    border.width: 1
                    border.color: root.c.line
                    Column {
                        id: serverColumn
                        x: 12
                        y: 10
                        width: parent.width - 24
                        spacing: 6
                        BrimText {
                            width: parent.width
                            elide: Text.ElideRight
                            text: modelData.name + (modelData.pinned ? " · " + root.view.t.server_builtin : "")
                            color: root.c.text
                            font.pixelSize: 13
                            font.bold: true
                        }
                        BrimText {
                            width: parent.width
                            visible: modelData.url !== ""
                            elide: Text.ElideMiddle
                            text: modelData.url
                            color: root.c.muted
                            font.pixelSize: 11
                        }
                        BrimText {
                            width: parent.width
                            wrapMode: Text.Wrap
                            text: root.serverState(modelData)
                            color: modelData.state === "error" ? root.c.danger : (modelData.state === "ok" ? root.c.ok : root.c.muted)
                            font.pixelSize: 11
                        }
                        Flow {
                            width: parent.width
                            spacing: 8
                            visible: !modelData.pinned
                            BrimButton {
                                text: modelData.enabled ? root.view.t.server_disable : root.view.t.server_enable
                                palette_: root.c
                                onClicked: brim.toggleServer(modelData.name, !modelData.enabled)
                            }
                            BrimButton {
                                text: root.view.t.remove_server
                                danger: true
                                palette_: root.c
                                onClicked: brim.removeServer(modelData.name)
                            }
                        }
                    }
                }
            }
            FieldInput {
                id: serverName
                width: parent.width
                c: root.c
                label: root.view.t.server_name
            }
            FieldInput {
                id: serverUrl
                width: parent.width
                c: root.c
                label: root.view.t.server_url
                hint: "http://127.0.0.1:3001/mcp"
            }
            FieldInput {
                id: serverHeader
                width: parent.width
                c: root.c
                label: root.view.t.server_header
            }
            BrimButton {
                text: root.view.t.add_server
                palette_: root.c
                onClicked: {
                    if (brim.addServer(serverName.value, serverUrl.value, serverHeader.value)) {
                        serverName.reset()
                        serverUrl.reset()
                        serverHeader.reset()
                    }
                }
            }
            BrimText {
                visible: root.view.mcp_port !== null && root.view.mcp_port !== undefined
                text: root.view.t.port_note + " " + root.view.mcp_port
                color: root.c.muted
                font.pixelSize: 12
            }
        }
    }
}
