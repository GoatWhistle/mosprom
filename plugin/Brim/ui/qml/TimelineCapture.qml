import QtQuick 2.7

Item {
    id: capture
    property var list: null
    property var frame: null
    property string folder: ""
    property bool active: false
    property int page: 0
    readonly property int overlap: 48
    readonly property int maxPages: 200
    signal finished(int pages, string error)

    function start(path) {
        folder = path
        page = 0
        active = true
        list.followEnd = false
        list.positionViewAtBeginning()
        tick.restart()
    }

    function fileName(number) {
        return folder + "/chat_" + (number < 10 ? "0" : "") + number + ".png"
    }

    function finish(error) {
        active = false
        list.jumpToEnd()
        finished(page, error)
    }

    function advance() {
        if (list.atYEnd || list.contentHeight <= list.height || page >= maxPages) {
            finish("")
            return
        }
        var last = list.originY + list.contentHeight - list.height
        list.contentY = Math.min(last, list.contentY + list.height - overlap)
        tick.restart()
    }

    Timer {
        id: tick
        interval: 220
        onTriggered: {
            var ok = capture.frame.grabToImage(function(result) {
                if (!result.saveToFile(capture.fileName(capture.page + 1))) {
                    capture.finish("saveToFile " + capture.fileName(capture.page + 1))
                    return
                }
                capture.page += 1
                capture.advance()
            }, Qt.size(capture.frame.width * 2, capture.frame.height * 2))
            if (!ok)
                capture.finish("grabToImage")
        }
    }
}
