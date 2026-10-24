import QtQuick 2.7
import QtQuick.Window 2.2

Window {
    id: window
    width: 980
    height: 720
    minimumWidth: 400
    minimumHeight: 480
    title: "Brim"
    visible: false
    color: panel.c.bg

    function present() {
        visible = true
        raise()
        requestActivate()
    }

    function openSettings() {
        panel.openSettings()
        present()
    }

    onClosing: {
        panel.settingsOpen = false
    }

    ChatPanel {
        id: panel
        anchors.fill: parent
    }
}
