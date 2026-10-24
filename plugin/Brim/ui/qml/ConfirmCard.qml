import QtQuick 2.7

Rectangle {
    id: root
    property var entry: ({})
    property var t: ({})
    property var c: ({})
    property bool active: false
    signal decide(string decision)

    width: parent ? parent.width : 300
    height: column.height + 28
    radius: 0
    color: c.panel
    border.width: active ? 2 : 1
    border.color: active ? c.accent : c.line
    transformOrigin: Item.Top

    function announce() {
        enter.start()
        if (active)
            ring.start()
    }
    NumberAnimation { id: enter; target: root; property: "scale"; from: 0.95; to: 1; duration: 200; easing.type: Easing.OutQuint }

    Rectangle {
        id: glow
        anchors.fill: parent
        anchors.margins: -4
        radius: root.radius + 4
        color: "transparent"
        border.width: 2
        border.color: root.c.accent
        opacity: 0
        SequentialAnimation {
            id: ring
            loops: 2
            NumberAnimation { target: glow; property: "opacity"; to: 0.8; duration: 160 }
            NumberAnimation { target: glow; property: "opacity"; to: 0; duration: 160 }
        }
    }

    function label(item) {
        return root.t["op_" + item.kind] || item.kind
    }

    function detail(item) {
        if (item.kind === "external")
            return item.target + "\n" + item.detail
        if (item.target)
            return item.target + ": " + item.detail
        return item.detail || "—"
    }

    function risk(item) {
        if (!item.risky)
            return ""
        return (root.t["risk_" + item.reason] || item.reason) + (item.limits ? " " + item.limits : "")
    }

    Column {
        id: column
        x: 16
        y: 14
        width: parent.width - 32
        spacing: 10

        BrimText {
            text: (root.t.confirmation || "") + (root.entry.server && root.entry.server !== "brim" ? " · " + root.entry.server : "")
            color: root.c.accentText
            font.family: "JetBrains Mono"
            font.pixelSize: 11
            font.weight: Font.DemiBold
            font.capitalization: Font.AllUppercase
            font.letterSpacing: 0.4
        }
        SelectableText {
            width: parent.width
            visible: text !== ""
            text: root.entry.explanation || ""
            textColor: root.c.text
        }
        Rectangle {
            width: parent.width
            height: rows.height
            radius: 0
            color: root.c.bg
            clip: true
            Column {
                id: rows
                width: parent.width
                Repeater {
                    model: root.entry.items || []
                    delegate: Item {
                        width: rows.width
                        height: Math.max(opKind.implicitHeight, opColumn.height) + 16
                        Rectangle {
                            visible: index > 0
                            width: parent.width
                            height: 1
                            color: root.c.line
                        }
                        BrimText {
                            id: opKind
                            x: 12
                            y: 8
                            width: Math.min(150, rows.width * 0.34)
                            wrapMode: Text.Wrap
                            text: root.label(modelData)
                            color: modelData.risky ? root.c.danger : root.c.muted
                            font.pixelSize: 12
                            font.bold: !!modelData.risky
                        }
                        Column {
                            id: opColumn
                            x: opKind.width + 20
                            y: 8
                            width: rows.width - opKind.width - 32
                            spacing: 2
                            SelectableText {
                                width: parent.width
                                text: root.detail(modelData)
                                textColor: root.c.text
                                font.pixelSize: 13
                            }
                            BrimText {
                                width: parent.width
                                visible: !!modelData.risky
                                wrapMode: Text.Wrap
                                text: root.risk(modelData)
                                color: root.c.danger
                                font.pixelSize: 12
                            }
                        }
                    }
                }
            }
        }
        Flow {
            width: parent.width
            spacing: 8
            visible: root.active
            BrimButton {
                text: root.t.apply || ""
                primary: true
                palette_: root.c
                onClicked: root.decide("accept")
            }
            BrimButton {
                text: root.t.reject || ""
                danger: true
                palette_: root.c
                onClicked: root.decide("reject")
            }
        }
        BrimText {
            visible: root.active
            width: parent.width
            wrapMode: Text.Wrap
            text: root.t.confirm_comment_hint || ""
            color: root.c.muted
            font.pixelSize: 11
        }
    }
}
