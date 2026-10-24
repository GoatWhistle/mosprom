import json

from PyQt5.QtCore import QObject, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QDesktopServices, QGuiApplication

from .runner import ThreadRunner


def local_path(value):
    url = QUrl(value)
    return url.toLocalFile() if url.isLocalFile() else str(value)


class ChatController(QObject):
    viewChanged = pyqtSignal()
    panelWidthChanged = pyqtSignal()
    captureRequested = pyqtSignal(str, arguments=["path"])
    _invoke = pyqtSignal(object)

    def __init__(self, build_presenter, settings=None, parent=None):
        QObject.__init__(self, parent)
        self._settings = settings
        self._invoke.connect(self._run_invoked)
        self._runner = ThreadRunner(self.post)
        self._presenter = build_presenter(self._runner, self._publish)
        self._last = None
        self._listeners = []
        self._cache = self._presenter.view()

    def add_view_listener(self, listener):
        self._listeners.append(listener)
        listener(self._cache)

    def post(self, function):
        self._invoke.emit(function)

    @pyqtSlot(object)
    def _run_invoked(self, function):
        function()

    def _publish(self):
        view = self._presenter.view()
        encoded = json.dumps(view, sort_keys=True, default=str)
        if encoded == self._last:
            return
        self._last = encoded
        self._cache = view
        self.viewChanged.emit()
        for listener in self._listeners:
            listener(view)

    @pyqtProperty("QVariantMap", notify=viewChanged)
    def view(self):
        return self._cache

    @pyqtProperty(int, notify=panelWidthChanged)
    def panelWidth(self):
        return self._settings.panel_width() if self._settings is not None else 0

    @pyqtSlot(int)
    def setPanelWidth(self, value):
        if self._settings is not None:
            self._settings.set_panel_width(value)
            self.panelWidthChanged.emit()

    @pyqtProperty(str, notify=viewChanged)
    def exportRoot(self):
        root = self._settings.export_root() if self._settings is not None else ""
        return QUrl.fromLocalFile(root).toString() if root else ""

    @pyqtSlot(str)
    def exportChat(self, folder):
        self._presenter.export(local_path(folder), self.captureRequested.emit)

    @pyqtSlot(int, str)
    def captureDone(self, pages, error):
        self._presenter.capture_done(pages, error)

    @property
    def presenter(self):
        return self._presenter

    def open_path(self, path):
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def start(self):
        self._presenter.start()
        self._publish()

    def shutdown(self):
        self._runner.stop()

    @pyqtSlot(str)
    def send(self, text):
        self._presenter.send(text)

    @pyqtSlot()
    def newChat(self):
        self._presenter.new_conversation()

    @pyqtSlot(str)
    def openChat(self, conversation_id):
        self._presenter.open_conversation(conversation_id)

    @pyqtSlot()
    def newChatFromScene(self):
        self._presenter.new_conversation(from_scene=True)

    @pyqtSlot(str)
    def setDraft(self, text):
        self._presenter.set_draft(text)

    @pyqtSlot()
    def cancelSwitch(self):
        self._presenter.cancel_switch()

    @pyqtSlot()
    def stopAndSwitch(self):
        self._presenter.stop_and_switch()

    @pyqtSlot()
    def retrySwitch(self):
        self._presenter.retry_switch()

    @pyqtSlot()
    def recoverWorkspace(self):
        self._presenter.recover_workspace()

    @pyqtSlot(str)
    def setMode(self, mode):
        self._presenter.set_mode(mode)

    @pyqtSlot(str)
    def setSkill(self, name):
        self._presenter.set_skill(name)

    @pyqtSlot(str)
    def attach(self, url):
        self._presenter.attach(local_path(url))

    @pyqtSlot(int)
    def removeAttachment(self, index):
        self._presenter.remove_attachment(index)

    @pyqtSlot(str, str)
    def confirm(self, decision, text):
        self._presenter.confirm(decision, text)

    @pyqtSlot()
    def stop(self):
        self._presenter.stop()

    @pyqtSlot()
    def openFolder(self):
        self._presenter.open_folder()

    @pyqtSlot(str)
    def openPath(self, path):
        self._presenter.open_path(path)

    @pyqtSlot(str, str, str, str, str, result=bool)
    def applySettings(self, llm_url, model, key, language, theme):
        return self._presenter.apply_settings(llm_url, model, key, language, theme)

    @pyqtSlot(str, str)
    def setInterface(self, language, theme):
        self._presenter.set_interface(language, theme)

    @pyqtSlot(str, str, str, result=bool)
    def addServer(self, name, url, header):
        return self._presenter.add_server(name, url, header)

    @pyqtSlot(str, bool)
    def toggleServer(self, name, enabled):
        self._presenter.toggle_server(name, enabled)

    @pyqtSlot(str)
    def removeServer(self, name):
        self._presenter.remove_server(name)

    @pyqtSlot()
    def checkConnection(self):
        self._presenter.check_connection()

    @pyqtSlot()
    def dismissNotice(self):
        self._presenter.state.notice = None
        self._publish()

    @pyqtSlot(str)
    def copyText(self, text):
        QGuiApplication.clipboard().setText(text)
