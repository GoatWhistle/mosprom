import QtQuick 2.7

Item {
    id: root
    property color base: "#e3e8eb"
    property color accent: "#0277bd"
    property bool intro: false
    property bool looping: false
    property bool reduced: false
    property int ringStagger: 120
    property int ringDuration: 280
    property int loopPeriod: 3200
    readonly property int size: Math.max(6, Math.round(Math.min(width, height)))
    readonly property int stroke: Math.max(1, Math.round(size * 8 / 164))
    readonly property int gap: Math.max(1, Math.round(size * 10 / 164))
    readonly property int step: stroke + gap
    readonly property int outerRadius: Math.round(size * 62 / 164)
    readonly property int contentLeft: Math.round((width - size) / 2)
    readonly property int contentTop: Math.round((height - size) / 2)

    implicitWidth: 32
    implicitHeight: 32

    function play() {
        if (reduced)
            return
        part.scale = 0.6
        ring1.opacity = 0
        ring2.opacity = 0
        ring3.opacity = 0
        introAnimation.restart()
    }

    function settle() {
        var rings = [ring1, ring2, ring3]
        for (var i = 0; i < rings.length; i++) {
            rings[i].opacity = 1
            rings[i].scale = 1
        }
        part.scale = 1
    }

    onLoopingChanged: if (!looping) settle()
    Component.onCompleted: if (intro) play()

    Rectangle {
        id: ring3
        x: root.contentLeft
        y: root.contentTop
        width: root.size
        height: width
        radius: root.outerRadius
        color: "transparent"
        border.width: root.stroke
        border.color: root.accent
    }

    Rectangle {
        id: ring2
        x: root.contentLeft + root.step
        y: root.contentTop + root.step
        width: root.size - 2 * root.step
        height: width
        radius: Math.max(1, root.outerRadius - root.step)
        color: "transparent"
        border.width: root.stroke
        border.color: root.base
    }

    Rectangle {
        id: ring1
        x: root.contentLeft + 2 * root.step
        y: root.contentTop + 2 * root.step
        width: root.size - 4 * root.step
        height: width
        radius: Math.max(1, root.outerRadius - 2 * root.step)
        color: "transparent"
        border.width: root.stroke
        border.color: root.base
    }

    Rectangle {
        id: part
        x: root.contentLeft + 3 * root.step
        y: root.contentTop + 3 * root.step
        width: Math.max(1, root.size - 6 * root.step)
        height: width
        radius: Math.max(1, root.outerRadius - 3 * root.step)
        color: root.base
    }

    ParallelAnimation {
        id: introAnimation
        NumberAnimation { target: part; property: "scale"; to: 1; duration: root.ringDuration; easing.type: Easing.OutCubic }
        RingIn { ring: ring1; delay: root.ringStagger }
        RingIn { ring: ring2; delay: root.ringStagger * 2 }
        RingIn { ring: ring3; delay: root.ringStagger * 3 }
    }

    RingLoop { ring: ring1; delay: root.ringStagger; period: root.loopPeriod; running: root.looping && !root.reduced && root.visible }
    RingLoop { ring: ring2; delay: root.ringStagger * 2; period: root.loopPeriod; running: root.looping && !root.reduced && root.visible }
    RingLoop { ring: ring3; delay: root.ringStagger * 3; period: root.loopPeriod; running: root.looping && !root.reduced && root.visible }
}
