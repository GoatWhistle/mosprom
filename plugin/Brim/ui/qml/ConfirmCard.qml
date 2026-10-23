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
    radius: 14
    color: c.panel
    border.width: active ? 2 : 1
    border.color: active ? c.accent : c.line
    opacity: active || !!entry.decision ? 1.0 : 0.7

    Column {
        id: column
        x: 16
        y: 14
        width: parent.width - 32
        spacing: 10

        Text {
            text: root.t.confirmation || ""
            color: root.c.accentText
            font.bold: true
            font.pixelSize: 13
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
            radius: 10
            color: root.c.bg
            clip: true
            Column {
                id: rows
                width: parent.width
                Repeater {
                    model: root.entry.operations || []
                    delegate: Item {
                        width: rows.width
                        height: Math.max(opKind.implicitHeight, opText.implicitHeight) + 16
                        Rectangle {
                            visible: index > 0
                            width: parent.width
                            height: 1
                            color: root.c.line
                        }
                        Text {
                            id: opKind
                            x: 12
                            y: 8
                            width: Math.min(150, rows.width * 0.34)
                            wrapMode: Text.Wrap
                            text: root.t["op_" + modelData.kind] || modelData.kind
                            color: root.c.muted
                            font.pixelSize: 12
                        }
                        SelectableText {
                            id: opText
                            x: opKind.width + 20
                            y: 8
                            width: rows.width - opKind.width - 32
                            text: root.describe(modelData)
                            textColor: root.c.text
                            font.pixelSize: 13
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
                text: root.t.clarify || ""
                palette_: root.c
                onClicked: root.decide("clarify")
            }
            BrimButton {
                text: root.t.reject || ""
                danger: true
                palette_: root.c
                onClicked: root.decide("reject")
            }
        }
        Text {
            visible: root.active
            width: parent.width
            wrapMode: Text.Wrap
            text: root.t.clarify_hint || ""
            color: root.c.muted
            font.pixelSize: 11
        }
        Text {
            visible: !root.active && !!root.entry.decision
            text: root.t["decision_" + root.entry.decision] || ""
            color: root.entry.decision === "accept" ? root.c.ok : root.c.muted
            font.bold: true
            font.pixelSize: 12
        }
    }

    function describe(op) {
        var keys = ["mode", "profile_id", "material_id", "object_id", "name", "extruder", "position_mm", "rotation_deg", "scale", "import_as"]
        var parts = []
        if (op.key !== undefined)
            parts.push(op.key + " → " + (op.value !== undefined ? JSON.stringify(op.value) : "?"))
        for (var i = 0; i < keys.length; i++) {
            if (op[keys[i]] !== undefined)
                parts.push(keys[i] + ": " + (typeof op[keys[i]] === "string" ? op[keys[i]] : JSON.stringify(op[keys[i]])))
        }
        return parts.length ? parts.join("\n") : "—"
    }
}
