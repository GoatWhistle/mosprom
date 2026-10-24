import QtQuick 2.7

BrimText {
    id: root
    property string source: ""
    property int epoch: 0
    property int duration: 520
    property bool reduced: false
    property real progress: 1
    readonly property string glyphs: "G01XYZEF;#%.2345"

    text: progress >= 1 ? source : scrambled(source, progress)

    function scrambled(value, amount) {
        var shown = Math.floor(value.length * amount)
        var out = ""
        for (var i = 0; i < value.length; i++) {
            var ch = value.charAt(i)
            out += i < shown || ch === " " || ch === "\n" ? ch : glyphs.charAt(Math.floor(Math.random() * glyphs.length))
        }
        return out
    }

    onEpochChanged: {
        if (reduced || source.length === 0 || source.length > 64)
            return
        ticker.started = Date.now()
        progress = 0
        ticker.restart()
    }

    Timer {
        id: ticker
        property real started: 0
        interval: 33
        repeat: true
        onTriggered: {
            var value = (Date.now() - started) / root.duration
            root.progress = value >= 1 ? 1 : value + 0.0001
            if (value >= 1)
                stop()
        }
    }
}
