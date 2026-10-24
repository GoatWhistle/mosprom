import QtQuick 2.7

SequentialAnimation {
    id: root
    property Item ring: null
    property int delay: 0
    property int period: 3200

    loops: Animation.Infinite

    PropertyAction { target: root.ring; property: "opacity"; value: 0 }
    PropertyAction { target: root.ring; property: "scale"; value: 0.84 }
    PauseAnimation { duration: root.delay }
    ParallelAnimation {
        NumberAnimation { target: root.ring; property: "opacity"; to: 1; duration: root.period * 0.22; easing.type: Easing.OutCubic }
        NumberAnimation { target: root.ring; property: "scale"; to: 1; duration: root.period * 0.22; easing.type: Easing.OutCubic }
    }
    PauseAnimation { duration: root.period * 0.62 }
    ParallelAnimation {
        NumberAnimation { target: root.ring; property: "opacity"; to: 0; duration: root.period * 0.16 }
        NumberAnimation { target: root.ring; property: "scale"; to: 1.04; duration: root.period * 0.16 }
    }
    PauseAnimation { duration: 480 - root.delay }
}
