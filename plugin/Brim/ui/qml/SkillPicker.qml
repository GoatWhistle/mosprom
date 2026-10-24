import QtQuick 2.7

Item {
    id: root
    property var view: ({})
    property var c: ({})
    property bool open: false
    signal chosen(string name)

    width: chip.width
    height: 34

    function titleOf(name) {
        var skills = root.view.skill_options || []
        for (var i = 0; i < skills.length; i++)
            if (skills[i].name === name)
                return skills[i].title
        return root.view.t.skill_auto
    }

    Rectangle {
        id: chip
        anchors.verticalCenter: parent.verticalCenter
        width: label.implicitWidth + 34
        height: 26
        radius: 13
        color: area.containsMouse || root.open ? root.c.selected : "transparent"
        border.width: 1
        border.color: root.view.skill !== "" ? root.c.accent : root.c.line
        Behavior on color { ColorAnimation { duration: 120 } }

        BrimText {
            id: label
            x: 12
            anchors.verticalCenter: parent.verticalCenter
            text: root.titleOf(root.view.skill)
            color: root.c.text
            font.pixelSize: 12
            font.bold: root.view.skill !== ""
        }
        BrimText {
            anchors.right: parent.right
            anchors.rightMargin: 10
            anchors.verticalCenter: parent.verticalCenter
            text: root.open ? "▴" : "▾"
            color: root.c.muted
            font.pixelSize: 10
        }
        MouseArea {
            id: area
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.open = !root.open
        }
        HintBubble {
            shown: area.containsMouse && !root.open
            text: root.view.t.skill_hint
            c: root.c
            x: 0
            y: -height - 8
        }
    }

    Rectangle {
        id: menu
        visible: root.open
        z: 60
        x: 0
        y: -height - 6
        width: 260
        height: options.height + 12
        radius: 10
        color: root.c.panel
        border.width: 1
        border.color: root.c.line

        Column {
            id: options
            x: 6
            y: 6
            width: parent.width - 12
            Repeater {
                model: root.view.skill_options || []
                delegate: Rectangle {
                    width: options.width
                    height: 34
                    radius: 7
                    color: itemArea.containsMouse ? root.c.selected : "transparent"
                    BrimText {
                        x: 10
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width - 20
                        elide: Text.ElideRight
                        text: modelData.title
                        color: modelData.name === root.view.skill ? root.c.accent : root.c.text
                        font.pixelSize: 13
                        font.bold: modelData.name === root.view.skill
                    }
                    MouseArea {
                        id: itemArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.open = false
                            root.chosen(modelData.name)
                        }
                    }
                }
            }
        }
    }
}
