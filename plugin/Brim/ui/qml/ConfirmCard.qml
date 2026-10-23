import QtQuick 2.7

Rectangle {
    id: root
    property var entry: ({})
    property var t: ({})
    property var c: ({})
    property bool active: false
    signal decide(string decision)

    width: parent ? parent.width : 300
    height: column.height + 24
    radius: 8
    color: c.panel
    border.width: 1
    border.color: active ? c.accent : c.line

    Column {
        id: column
        x: 14
        y: 12
        width: parent.width - 28
        spacing: 8

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
        Repeater {
            model: root.entry.operations || []
            delegate: Row {
                spacing: 8
                Text {
                    text: "•"
                    color: root.c.accent
                    font.pixelSize: 14
                }
                SelectableText {
                    width: column.width - 24
                    text: (root.t["op_" + modelData.kind] || modelData.kind) + summarize(modelData)
                    textColor: root.c.text
                    font.pixelSize: 13
                }
            }
        }
        Row {
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
                palette_: root.c
                onClicked: root.decide("reject")
            }
            BrimButton {
                text: root.t.clarify || ""
                palette_: root.c
                onClicked: root.decide("clarify")
            }
        }
        Text {
            visible: root.active
            width: parent.width
            wrapMode: Text.Wrap
            text: root.t.clarify_hint || ""
            color: root.c.muted
            font.pixelSize: 12
        }
        Text {
            visible: !root.active && !!root.entry.decision
            text: root.t["decision_" + root.entry.decision] || ""
            color: root.c.muted
            font.pixelSize: 12
        }
    }

    function summarize(op) {
        var keys = ["mode", "profile_id", "material_id", "key", "value", "object_id", "name", "extruder", "position_mm", "rotation_deg", "scale", "import_as"]
        var parts = []
        for (var i = 0; i < keys.length; i++) {
            if (op[keys[i]] !== undefined)
                parts.push(keys[i] + "=" + JSON.stringify(op[keys[i]]))
        }
        return parts.length ? ": " + parts.join(", ") : ""
    }
}
