import QtQuick 2.7

Item {
    id: dock
    property var topbar: null
    property var jobSpecs: null
    property bool open: false
    readonly property real minWidth: 360
    property real preferredWidth: brim.panelWidth >= minWidth ? brim.panelWidth : 440
    property real slide: open ? 0 : width + 2

    z: 100
    anchors.right: parent ? parent.right : undefined
    y: topbar ? topbar.y + topbar.height : 0
    height: parent ? parent.height - y : 0
    width: Math.max(minWidth, Math.min(preferredWidth, parent ? parent.width * 0.7 : preferredWidth))

    Behavior on slide { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }

    function present() {
        open = true
    }

    function openSettings() {
        panel.openSettings()
        open = true
    }

    Binding {
        target: dock.jobSpecs
        property: "anchors.rightMargin"
        value: dock.width - dock.slide + 12
        when: !!dock.jobSpecs && dock.slide < dock.width
    }

    Rectangle {
        id: tab
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        width: 30
        height: 96
        radius: 4
        color: tabArea.containsMouse ? panel.c.accentHover : panel.c.accent
        opacity: dock.open ? 0 : 1
        visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: 140 } }
        BrandMark {
            anchors.horizontalCenter: parent.horizontalCenter
            y: 10
            width: 18
            height: 18
            base: panel.c.actionText
            accent: panel.c.actionText
        }
        BrandWordmark {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.horizontalCenterOffset: 1
            y: 52
            height: 11
            rotation: -90
            dark: true
        }
        MouseArea {
            id: tabArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: dock.open = true
        }
    }

    Item {
        id: sheet
        width: dock.width
        height: dock.height
        x: dock.slide
        visible: dock.slide < dock.width
        clip: true

        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.AllButtons
            onWheel: wheel.accepted = true
        }

        ChatPanel {
            id: panel
            anchors.fill: parent
            closable: true
            onCloseRequested: dock.open = false
        }

        Rectangle {
            width: 1
            height: parent.height
            color: panel.c.line
        }

        MouseArea {
            width: 6
            height: parent.height
            hoverEnabled: true
            cursorShape: Qt.SizeHorCursor
            property real startX: 0
            property real startWidth: 0
            onPressed: {
                startX = mapToItem(null, mouse.x, 0).x
                startWidth = dock.width
            }
            onPositionChanged: {
                if (pressed)
                    dock.preferredWidth = Math.max(dock.minWidth, startWidth + startX - mapToItem(null, mouse.x, 0).x)
            }
            onReleased: brim.setPanelWidth(Math.round(dock.width))
        }
    }
}
