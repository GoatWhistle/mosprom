import QtQuick 2.7

SequentialAnimation {
    id: root
    property Item ring: null
    property int delay: 0
    property int duration: 280

    PauseAnimation { duration: root.delay }
    ParallelAnimation {
        NumberAnimation { target: root.ring; property: "opacity"; from: 0; to: 1; duration: root.duration; easing.type: Easing.OutCubic }
        NumberAnimation { target: root.ring; property: "scale"; from: 0.84; to: 1; duration: root.duration; easing.type: Easing.OutCubic }
    }
}
