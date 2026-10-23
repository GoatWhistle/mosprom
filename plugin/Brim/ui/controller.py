import json

from PyQt5.QtCore import QObject, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QGuiApplication

from .runner import ThreadRunner


def local_path(value):
    url = QUrl(value)
    return url.toLocalFile() if url.isLocalFile() else str(value)


class ChatController(QObject):
    viewChanged = pyqtSignal()
    _invoke = pyqtSignal(object)

    def __init__(self, build_presenter, parent=None):
        QObject.__init__(self, parent)
        self._invoke.connect(self._run_invoked)
        self._runner = ThreadRunner(self.post)
        self._presenter = build_presenter(self._runner, self._publish)
        self._last = None
        self._cache = self._presenter.view()

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

    @pyqtProperty("QVariantMap", notify=viewChanged)
    def view(self):
        return self._cache

    @property
    def presenter(self):
        return self._presenter

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

    @pyqtSlot(str)
    def setMode(self, mode):
        self._presenter.set_mode(mode)

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

    @pyqtSlot(str, str)
    def saveArtifact(self, kind, url):
        self._presenter.save_artifact(kind, local_path(url))

    @pyqtSlot(str, str, str, str, str, str, result=bool)
    def applySettings(self, backend, llm_url, model, key, language, theme):
        return self._presenter.apply_settings(backend, llm_url, model, key, language, theme)

    @pyqtSlot()
    def checkBackend(self):
        self._presenter.check_backend()

    @pyqtSlot()
    def dismissNotice(self):
        self._presenter.state.notice = None
        self._publish()

    @pyqtSlot(str)
    def copyText(self, text):
        QGuiApplication.clipboard().setText(text)
