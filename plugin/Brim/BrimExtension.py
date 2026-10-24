import os

from PyQt5.QtCore import QMetaObject, QTimer, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtQml import QQmlComponent, QQmlContext

from UM.Extension import Extension
from UM.Logger import Logger

from .composition import BrimRuntime
from .ui.dock import find_item
from .ui.strings import strings_for

QML_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "qml")
QML_PATH = os.path.join(QML_DIR, "Chat.qml")
DOCK_PATH = os.path.join(QML_DIR, "DockPanel.qml")


class BrimExtension(Extension):
    def __init__(self, application):
        Extension.__init__(self)
        self._application = application
        self._runtime = None
        self._window = None
        self._dock = None
        self._dock_parts = None
        self._failure = None
        try:
            self._runtime = BrimRuntime(application)
        except Exception as error:
            self._failure = error
            Logger.logException("e", "Brim failed to initialise: %s" % error)
        language = self._runtime.settings.language() if self._runtime is not None else "ru"
        strings = strings_for(language)
        self.setMenuName("Brim")
        self.addMenuItem(strings["menu_open"], self.openChat)
        self.addMenuItem(strings["menu_browser"], self.openInBrowser)
        self.addMenuItem(strings["menu_settings"], self.openSettings)
        ready = getattr(application, "engineCreatedSignal", None)
        if ready is not None and self._runtime is not None:
            ready.connect(self._start)
            ready.connect(self._watch_main_window)

    def _start(self):
        if self._runtime is None:
            return
        try:
            self._runtime.start()
        except Exception as error:
            Logger.logException("e", "Brim failed to start: %s" % error)
        exit_hook = getattr(self._application, "addOnExitCallback", None)
        if exit_hook is not None:
            exit_hook(self._runtime.shutdown)
        else:
            from PyQt5.QtCore import QCoreApplication

            QCoreApplication.instance().aboutToQuit.connect(self._runtime.shutdown)

    def _watch_main_window(self):
        changed = getattr(self._application, "mainWindowChanged", None)
        if changed is not None:
            changed.connect(lambda: QTimer.singleShot(0, self._ensure_dock))
        QTimer.singleShot(0, self._ensure_dock)

    def _ensure_dock(self):
        if self._dock is not None:
            return self._dock
        if self._runtime is None:
            return None
        main = getattr(self._application, "getMainWindow", lambda: None)()
        engine = getattr(self._application, "_qml_engine", None)
        if main is None or engine is None:
            return None
        topbar = find_item(main.contentItem(), "Topbar")
        host = topbar.parentItem() if topbar is not None else None
        if host is None:
            Logger.log("w", "Brim dock: slicer top bar not found, chat stays a window")
            return None
        context = QQmlContext(engine.rootContext(), host)
        context.setContextProperty("brim", self._runtime.controller)
        component = QQmlComponent(engine, QUrl.fromLocalFile(DOCK_PATH))
        dock = component.create(context)
        if dock is None:
            Logger.log("e", "Brim dock could not be created: %s" % [error.toString() for error in component.errors()])
            return None
        dock.setParent(host)
        dock.setParentItem(host)
        dock.setProperty("topbar", topbar)
        dock.setProperty("jobSpecs", find_item(host, "JobSpecs"))
        self._dock_parts = (context, component)
        self._dock = dock
        return dock

    def _ensure_window(self):
        if self._window is not None:
            return self._window
        if self._runtime is None:
            Logger.log("e", "Brim is unavailable: %s" % self._failure)
            return None
        self._start()
        context = {"brim": self._runtime.controller}
        creator = getattr(self._application, "createQmlComponent", None)
        if creator is not None:
            self._window = creator(QML_PATH, context)
        else:
            engine = self._application._qml_engine
            for name, value in context.items():
                engine.rootContext().setContextProperty(name, value)
            component = QQmlComponent(engine, QUrl.fromLocalFile(QML_PATH))
            self._window = component.create()
        if self._window is None:
            Logger.log("e", "Brim chat window could not be created from %s" % QML_PATH)
            return None
        main = getattr(self._application, "getMainWindow", lambda: None)()
        if main is not None and hasattr(self._window, "setTransientParent"):
            self._window.setTransientParent(main)
        return self._window

    def _target(self):
        return self._ensure_dock() or self._ensure_window()

    def openChat(self):
        window = self._target()
        if window is not None:
            QMetaObject.invokeMethod(window, "present")

    def openSettings(self):
        window = self._target()
        if window is not None:
            QMetaObject.invokeMethod(window, "openSettings")

    def openInBrowser(self):
        if self._runtime is None:
            Logger.log("e", "Brim is unavailable: %s" % self._failure)
            return
        self._start()
        url = self._runtime.web.url()
        if url is None:
            Logger.log("e", "Brim browser chat server is not running")
            return
        Logger.log("i", "Brim browser chat: http://127.0.0.1:%d/" % self._runtime.web.port())
        QDesktopServices.openUrl(QUrl(url))
