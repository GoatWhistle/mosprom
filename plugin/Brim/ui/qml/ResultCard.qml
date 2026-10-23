import QtQuick 2.7

Rectangle {
    id: root
    property var result: ({})
    property var t: ({})
    property var c: ({})
    signal save(string kind)

    height: column.height + 24
    radius: 8
    color: c.panel
    border.width: 1
    border.color: c.accent

    function duration(seconds) {
        if (seconds === undefined || seconds === null)
            return "—"
        var hours = Math.floor(seconds / 3600)
        var minutes = Math.round((seconds % 3600) / 60)
        return hours + " " + t.hours + " " + minutes + " " + t.minutes
    }

    function weight(values) {
        if (!values || values.length === 0)
            return "—"
        var total = 0
        for (var i = 0; i < values.length; i++)
            total += values[i]
        return total.toFixed(1) + " " + t.grams
    }

    Column {
        id: column
        x: 14
        y: 12
        width: parent.width - 28
        spacing: 6

        Text {
            text: root.t.result || ""
            color: root.c.accentText
            font.bold: true
            font.pixelSize: 13
        }
        Text {
            text: (root.t.print_time || "") + ": " + root.duration((root.result.summary || {}).print_time_seconds)
            color: root.c.text
            font.pixelSize: 13
        }
        Text {
            text: (root.t.material || "") + ": " + root.weight((root.result.summary || {}).material_weight_g)
            color: root.c.text
            font.pixelSize: 13
        }
        Row {
            spacing: 8
            BrimButton {
                text: root.t.save_gcode || ""
                palette_: root.c
                onClicked: root.save("gcode")
            }
            BrimButton {
                text: root.t.save_3mf || ""
                palette_: root.c
                onClicked: root.save("3mf")
            }
        }
    }
}
