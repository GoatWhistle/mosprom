import QtQuick 2.7

Rectangle {
    id: root
    property var result: ({})
    property var t: ({})
    property var c: ({})
    signal open(string path)

    height: column.height + 28
    radius: 0
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

        BrimText {
            text: root.t.result || ""
            color: root.c.accentText
            font.family: "JetBrains Mono"
            font.pixelSize: 11
            font.weight: Font.DemiBold
            font.capitalization: Font.AllUppercase
            font.letterSpacing: 0.4
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
                    height: 72
                    radius: 0
                    color: root.c.bg
                    Column {
                        anchors.centerIn: parent
                        spacing: 2
                        BrimText {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: modelData.value
                            color: root.c.text
                            font.family: "Handjet"
                            font.pixelSize: 34
                        }
                        BrimText {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: modelData.label
                            color: root.c.muted
                            font.pixelSize: 11
                        }
                    }
                }
            }
        }
        Repeater {
            model: ["gcode", "3mf"]
            delegate: SelectableText {
                width: column.width
                visible: !!(root.result.files || {})[modelData]
                text: (root.result.files || {})[modelData] || ""
                textColor: root.c.muted
                font.family: "JetBrains Mono"
                font.pixelSize: 11
            }
        }
        Flow {
            width: parent.width
            spacing: 8
            BrimButton {
                text: root.t.open_folder || ""
                primary: true
                palette_: root.c
                onClicked: root.open(root.result.folder || "")
            }
        }
    }
}
