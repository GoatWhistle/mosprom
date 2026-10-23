import os

from PyQt5.QtCore import QMetaObject, QUrl
from PyQt5.QtQml import QQmlComponent

from UM.Extension import Extension
from UM.Logger import Logger

from .composition import BrimRuntime
from .ui.strings import strings_for

QML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "qml", "Chat.qml")


class BrimExtension(Extension):
    def __init__(self, application):
        Extension.__init__(self)
        self._application = application
        self._runtime = None
        self._window = None
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
        self.addMenuItem(strings["menu_settings"], self.openSettings)
        ready = getattr(application, "engineCreatedSignal", None)
        if ready is not None and self._runtime is not None:
            ready.connect(self._start)

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

    def openChat(self):
        window = self._ensure_window()
        if window is not None:
            QMetaObject.invokeMethod(window, "present")

    def openSettings(self):
        window = self._ensure_window()
        if window is not None:
            QMetaObject.invokeMethod(window, "openSettings")
