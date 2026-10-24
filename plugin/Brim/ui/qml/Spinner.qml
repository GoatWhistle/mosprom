import QtQuick 2.7

Item {
    id: root
    property color color: "#0277bd"
    property color track: "#330277bd"
    property bool running: true
    property int period: 1600

    implicitWidth: 16
    implicitHeight: 16

    BrandMark {
        anchors.fill: parent
        base: root.track
        accent: root.color
        looping: root.running
        loopPeriod: root.period
        ringStagger: root.period / 16
    }
}
