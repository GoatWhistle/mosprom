import QtQuick 2.7

TextEdit {
    property color textColor: "#000000"
    readOnly: true
    selectByMouse: true
    wrapMode: TextEdit.Wrap
    textFormat: TextEdit.PlainText
    font.pixelSize: 14
    color: textColor
    selectionColor: "#ff8a3d"
    selectedTextColor: "#12130f"
}
