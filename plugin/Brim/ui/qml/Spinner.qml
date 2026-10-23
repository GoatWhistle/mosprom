import QtQuick 2.7

Item {
    id: root
    property color color: "#ff8a3d"
    property color track: "#33ff8a3d"
    property bool running: true
    property int period: 800
    property real lineWidth: Math.max(1.5, width / 9)

    implicitWidth: 16
    implicitHeight: 16

    Canvas {
        id: ring
        anchors.fill: parent
        onPaint: {
            var g = getContext("2d")
            var r = Math.min(width, height) / 2 - root.lineWidth
            g.clearRect(0, 0, width, height)
            g.lineWidth = root.lineWidth
            g.lineCap = "round"
            g.strokeStyle = root.track
            g.beginPath()
            g.arc(width / 2, height / 2, r, 0, Math.PI * 2, false)
            g.stroke()
            g.strokeStyle = root.color
            g.beginPath()
            g.arc(width / 2, height / 2, r, -Math.PI / 2, Math.PI / 3, false)
            g.stroke()
        }
        Connections {
            target: root
            onColorChanged: ring.requestPaint()
            onTrackChanged: ring.requestPaint()
        }
        RotationAnimation on rotation {
            running: root.running && root.visible
            loops: Animation.Infinite
            from: 0
            to: 360
            duration: root.period
        }
    }
}
