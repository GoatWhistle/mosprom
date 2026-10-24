import QtQuick 2.7

Rectangle {
    id: root
    property string name: ""
    property bool removable: false
    property var c: ({})
    signal removed()

    function extension() {
        var dot = name.lastIndexOf(".")
        return dot >= 0 ? name.substring(dot + 1).toUpperCase() : "FILE"
    }

    height: 26
    width: Math.min(220, badge.width + label.implicitWidth + (removable ? 44 : 28))
    radius: 13
    color: c.selected
    border.width: 1
    border.color: c.line

    Rectangle {
        id: badge
        x: 4
        anchors.verticalCenter: parent.verticalCenter
        width: ext.implicitWidth + 12
        height: 18
        radius: 9
        color: root.c.accent
        BrimText {
            id: ext
            anchors.centerIn: parent
            text: root.extension()
            font.pixelSize: 10
            font.bold: true
            color: root.c.actionText
        }
    }
    BrimText {
        id: label
        anchors.left: badge.right
        anchors.leftMargin: 8
        anchors.right: parent.right
        anchors.rightMargin: root.removable ? 26 : 10
        anchors.verticalCenter: parent.verticalCenter
        elide: Text.ElideMiddle
        text: root.name
        color: root.c.text
        font.pixelSize: 12
    }
    BrimText {
        visible: root.removable
        anchors.right: parent.right
        anchors.rightMargin: 9
        anchors.verticalCenter: parent.verticalCenter
        text: "×"
        color: root.c.muted
        font.pixelSize: 15
        MouseArea {
            anchors.fill: parent
            anchors.margins: -5
            cursorShape: Qt.PointingHandCursor
            onClicked: root.removed()
        }
    }
}
