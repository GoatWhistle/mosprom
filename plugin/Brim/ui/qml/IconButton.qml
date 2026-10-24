import QtQuick 2.7

Rectangle {
    id: root
    property string glyph: ""
    property var palette_: ({})
    property bool primary: false
    property bool enabledButton: true
    property string tip: ""
    readonly property bool hovered: area.containsMouse
    signal clicked()

    width: 34
    height: 34
    radius: 17
    activeFocusOnTab: true
    opacity: enabledButton ? 1.0 : 0.45
    color: primary ? (area.containsMouse && enabledButton ? palette_.accentHover : palette_.accent)
                   : (area.containsMouse && enabledButton ? palette_.selected : "transparent")
    border.width: activeFocus ? 1 : 0
    border.color: palette_.accent

    Behavior on color { ColorAnimation { duration: 120 } }

    Canvas {
        id: canvas
        anchors.centerIn: parent
        width: 18
        height: 18
        property color stroke: root.primary ? root.palette_.actionText : root.palette_.text
        onStrokeChanged: requestPaint()
        onPaint: {
            var g = getContext("2d")
            g.clearRect(0, 0, width, height)
            g.strokeStyle = stroke
            g.fillStyle = stroke
            g.lineWidth = 1.8
            g.lineCap = "round"
            g.lineJoin = "round"
            g.beginPath()
            if (root.glyph === "send") {
                g.moveTo(3, 9)
                g.lineTo(15, 9)
                g.moveTo(10, 4)
                g.lineTo(15, 9)
                g.lineTo(10, 14)
            } else if (root.glyph === "attach") {
                g.moveTo(14, 8)
                g.lineTo(8, 14)
                g.arc(6.5, 12.5, 2.1, Math.PI / 4, Math.PI * 1.25, false)
                g.lineTo(12.5, 4.5)
                g.arc(13.5, 5.5, 1.4, Math.PI * 1.25, Math.PI / 4, false)
                g.lineTo(15, 11)
            } else if (root.glyph === "menu") {
                g.moveTo(3, 5); g.lineTo(15, 5)
                g.moveTo(3, 9); g.lineTo(15, 9)
                g.moveTo(3, 13); g.lineTo(15, 13)
            } else if (root.glyph === "plus") {
                g.moveTo(9, 3); g.lineTo(9, 15)
                g.moveTo(3, 9); g.lineTo(15, 9)
            } else if (root.glyph === "gear") {
                g.arc(9, 9, 3, 0, Math.PI * 2, false)
                for (var i = 0; i < 8; i++) {
                    var a = i * Math.PI / 4
                    g.moveTo(9 + Math.cos(a) * 5.5, 9 + Math.sin(a) * 5.5)
                    g.lineTo(9 + Math.cos(a) * 7.5, 9 + Math.sin(a) * 7.5)
                }
            } else if (root.glyph === "close") {
                g.moveTo(4, 4); g.lineTo(14, 14)
                g.moveTo(14, 4); g.lineTo(4, 14)
            } else if (root.glyph === "stop") {
                g.rect(4, 4, 10, 10)
            } else if (root.glyph === "down") {
                g.moveTo(4, 7); g.lineTo(9, 12); g.lineTo(14, 7)
            } else if (root.glyph === "export") {
                g.moveTo(9, 11); g.lineTo(9, 2.5)
                g.moveTo(5.5, 6); g.lineTo(9, 2.5); g.lineTo(12.5, 6)
                g.moveTo(3, 10); g.lineTo(3, 15); g.lineTo(15, 15); g.lineTo(15, 10)
            } else if (root.glyph === "file") {
                g.moveTo(5, 2.5); g.lineTo(11, 2.5); g.lineTo(14, 5.5); g.lineTo(14, 15.5)
                g.lineTo(5, 15.5); g.closePath()
                g.moveTo(11, 2.5); g.lineTo(11, 5.5); g.lineTo(14, 5.5)
            }
            g.stroke()
        }
    }

    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: root.enabledButton ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: if (root.enabledButton) root.clicked()
    }

    Keys.onReturnPressed: if (enabledButton) clicked()
    Keys.onSpacePressed: if (enabledButton) clicked()
}
