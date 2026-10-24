import QtQuick 2.7

QtObject {
    property bool reducedMotion: false
    readonly property int durInstant: reducedMotion ? 1 : 80
    readonly property int durFast: reducedMotion ? 1 : 160
    readonly property int durFastExit: reducedMotion ? 1 : 110
    readonly property int durBase: reducedMotion ? 1 : 200
    readonly property int durExit: reducedMotion ? 1 : 140
    readonly property int durSlow: reducedMotion ? 1 : 320
    readonly property int durSpin: 800
    readonly property int durTravel: 1000
    readonly property int easeOut: Easing.OutQuint
    readonly property int easeInOut: Easing.InOutQuart
    readonly property int slowThinkingSeconds: 60
    readonly property string fontMono: "JetBrains Mono"
    readonly property string fontSans: "Onest"
    readonly property string fontDisplay: "Handjet"
}
