import QtQuick 2.7

Item {
    id: root
    property int markSize: 28
    property bool dark: true
    property color base: dark ? "#e3e8eb" : "#14181b"
    property color accent: "#0277bd"
    property bool intro: false
    property bool reduced: false

    implicitWidth: word.x + word.width
    implicitHeight: markSize
    width: implicitWidth
    height: implicitHeight

    BrandMark {
        width: root.markSize
        height: root.markSize
        base: root.base
        accent: root.accent
        intro: root.intro
        reduced: root.reduced
    }

    BrandWordmark {
        id: word
        x: root.markSize + Math.round(root.markSize * 0.25)
        height: Math.round(root.markSize * 0.62)
        y: Math.round((root.markSize - height) / 2)
        dark: root.dark
    }
}
