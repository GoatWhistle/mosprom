import QtQuick 2.7

TextEdit {
    id: field
    font.family: "Onest"
    property color textColor: "#000000"
    readOnly: true
    selectByMouse: true
    wrapMode: TextEdit.Wrap
    textFormat: TextEdit.PlainText
    font.pixelSize: 14
    color: textColor
    selectionColor: "#ff8a3d"
    selectedTextColor: "#12130f"
    onLinkActivated: Qt.openUrlExternally(link)

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.NoButton
        cursorShape: field.hoveredLink !== "" ? Qt.PointingHandCursor : Qt.IBeamCursor
    }
}
