import QtQuick 2.7

Rectangle {
    id: root
    property string text: ""
    property bool primary: false
    property bool danger: false
    property bool enabledButton: true
    property var palette_: ({})
    property int epoch: 0
    property bool reduced: false
    signal clicked()

    implicitWidth: label.implicitWidth + 28
    implicitHeight: 32
    radius: 16
    activeFocusOnTab: true
    opacity: enabledButton ? 1.0 : 0.45
    color: primary ? (area.containsMouse && enabledButton ? palette_.accentHover : palette_.accent)
                   : (area.containsMouse && enabledButton ? palette_.selected : "transparent")
    border.width: primary ? 0 : 1
    border.color: activeFocus ? palette_.accent : (danger ? palette_.danger : palette_.line)

    Behavior on color { ColorAnimation { duration: 120 } }

    ScrambleText {
        id: label
        anchors.centerIn: parent
        source: root.text
        epoch: root.epoch
        reduced: root.reduced
        font.pixelSize: 13
        font.bold: root.primary
        color: root.primary ? root.palette_.actionText : (root.danger ? root.palette_.danger : root.palette_.text)
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
