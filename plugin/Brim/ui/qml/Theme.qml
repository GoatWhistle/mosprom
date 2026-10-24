import QtQuick 2.7

QtObject {
    property bool reducedMotion: false
    readonly property var darkPalette: ({
        bg: "#14181b", panel: "#1f2427", selected: "#283035", hover: "#283035",
        userBg: "#163449", userText: "#e4f1fb", line: "#3a4248", text: "#e3e8eb",
        muted: "#8f9aa2", accent: "#0277bd", accentHover: "#026aa8", accentText: "#58a5f0",
        actionText: "#ffffff", danger: "#ff8a80", ok: "#8fd6a8"
    })
    readonly property var lightPalette: ({
        bg: "#f4f6f8", panel: "#ffffff", selected: "#e9edf0", hover: "#e9edf0",
        userBg: "#dcedf9", userText: "#0b2a40", line: "#d6dce0", text: "#1f2427",
        muted: "#5b666e", accent: "#0277bd", accentHover: "#026aa8", accentText: "#01579b",
        actionText: "#ffffff", danger: "#b3261e", ok: "#1f6e43"
    })
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
