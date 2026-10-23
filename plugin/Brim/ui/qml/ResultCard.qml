import QtQuick 2.7

Rectangle {
    id: root
    property var result: ({})
    property var t: ({})
    property var c: ({})
    signal save(string kind)

    height: column.height + 28
    radius: 14
    color: c.panel
    border.width: 2
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
        x: 16
        y: 14
        width: parent.width - 32
        spacing: 10

        Text {
            text: root.t.result || ""
            color: root.c.accentText
            font.bold: true
            font.pixelSize: 13
        }
        Row {
            spacing: 10
            Repeater {
                model: [
                    {label: root.t.print_time || "", value: root.duration((root.result.summary || {}).print_time_seconds)},
                    {label: root.t.material || "", value: root.weight((root.result.summary || {}).material_weight_g)}
                ]
                delegate: Rectangle {
                    width: (column.width - 10) / 2
                    height: 56
                    radius: 10
                    color: root.c.bg
                    Column {
                        anchors.centerIn: parent
                        spacing: 2
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: modelData.value
                            color: root.c.text
                            font.pixelSize: 16
                            font.bold: true
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: modelData.label
                            color: root.c.muted
                            font.pixelSize: 11
                        }
                    }
                }
            }
        }
        Flow {
            width: parent.width
            spacing: 8
            BrimButton {
                text: root.t.save_gcode || ""
                primary: true
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
