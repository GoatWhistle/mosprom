import QtQuick 2.7

Item {
    id: root
    property color nozzle: "#0277bd"
    property int layers: 8
    property int layerDuration: 280
    property int stagger: 40
    property int fadeDuration: 200
    property bool reduced: false
    property color surface: "#14181b"
    property var pending: null

    visible: false
    z: 1000

    function run(target, apply) {
        if (reduced || width <= 0) {
            apply()
            return
        }
        surface = target
        pending = apply
        opacity = 1
        visible = true
        for (var i = 0; i < bands.count; i++)
            bands.itemAt(i).start()
        cover.restart()
    }

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.AllButtons
        hoverEnabled: true
    }

    Repeater {
        id: bands
        model: root.layers
        Item {
            id: band
            readonly property bool fromRight: (root.layers - 1 - index) % 2 === 1
            width: root.width
            height: Math.ceil(root.height / root.layers) + 1
            y: index * root.height / root.layers
            x: fromRight ? root.width : -root.width

            function start() {
                x = fromRight ? root.width : -root.width
                slide.restart()
            }

            Rectangle {
                anchors.fill: parent
                color: root.surface
            }
            Rectangle {
                width: 3
                height: parent.height
                x: band.fromRight ? -width : parent.width
                color: root.nozzle
            }
            SequentialAnimation {
                id: slide
                PauseAnimation { duration: root.stagger * (root.layers - 1 - index) }
                NumberAnimation { target: band; property: "x"; to: 0; duration: root.layerDuration; easing.type: Easing.OutQuint }
            }
        }
    }

    Timer {
        id: cover
        interval: root.layerDuration + root.stagger * (root.layers - 1) + 16
        onTriggered: {
            var apply = root.pending
            root.pending = null
            if (apply)
                apply()
            fade.restart()
        }
    }

    SequentialAnimation {
        id: fade
        NumberAnimation { target: root; property: "opacity"; to: 0; duration: root.fadeDuration; easing.type: Easing.OutCubic }
        PropertyAction { target: root; property: "visible"; value: false }
    }
}
