import QtQuick 2.7

Rectangle {
    id: root
    property bool shown: false
    property string text: ""
    property var c: ({})

    visible: opacity > 0
    opacity: shown ? 1 : 0
    z: 50
    x: parent ? parent.width - width : 0
    y: parent ? parent.height + 8 : 0
    width: Math.min(260, label.implicitWidth + 20)
    height: label.height + 14
    radius: 2
    color: c.panel
    border.width: 1
    border.color: c.line
    Behavior on opacity { NumberAnimation { duration: 120 } }

    BrimText {
        id: label
        x: 10
        y: 7
        width: parent.width - 20
        wrapMode: Text.Wrap
        text: root.text
        color: root.c.text
        font.pixelSize: 12
    }
}
