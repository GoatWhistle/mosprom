import json
import os
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5 import sip
from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtQml import QQmlApplicationEngine
from PyQt5.QtQuick import QQuickWindow

import playground_scenarios as scenarios
from Brim.agent import ask_user
from Brim.agent.transcript import call_name
from Brim.browser.bridge import WebBridge
from Brim.browser.server import WebChatServer
from Brim.chat.presenter import ChatPresenter
from Brim.settings import MemoryStore, PluginSettings
from Brim.ui.controller import ChatController
from Brim.workspace.service import WorkspaceService
from Brim.workspace.store import WorkspaceStore

QML = os.path.join(ROOT, "Brim", "ui", "qml", "Chat.qml")
WEB = os.path.join(ROOT, "Brim", "web")


class ScenePort(object):
    def __init__(self):
        self.scene = []

    def lock_changes(self, locked):
        return None

    def scene_is_empty(self):
        return not self.scene

    def save_workspace(self, path):
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("3D/3dmodel.model", "<model></model>")

    def load_workspace(self, path):
        return None

    def clear_workspace(self):
        self.scene = []


class Hub(object):
    def refresh(self):
        return []

    def status(self):
        return {"brim": {"state": "ok", "tools": 15, "error": None}}


class Llm(object):
    def models(self):
        return ["playground"]


class ScriptedTurn(object):
    def __init__(self, conversation, emit):
        self.conversation = conversation
        self.emit_to = emit
        self.cancelled = False
        self.pending_confirm = None

    def emit(self, kind, payload=None):
        self.emit_to(self, kind, payload or {})

    def append(self, message):
        self.conversation.append(message)
        self.emit("changed")

    def run(self, steps):
        delay = 0
        for pause, action in steps.items:
            delay += pause
            QTimer.singleShot(delay, lambda action=action: None if self.cancelled else action(self))

    def start(self, text=None, attachments=None, answer=None):
        if answer is not None:
            call_id = self._pending_question()
            if call_id is not None:
                self.conversation.append({"role": "tool", "tool_call_id": call_id, "brim_status": "ok",
                                          "brim_server": "brim", "content": json.dumps({"answer": answer},
                                                                                       ensure_ascii=False)})
            self.run(scenarios.after_answer())
            return self
        self.conversation.append({"role": "user", "content": text or "", "brim_attachments": attachments or []})
        self.conversation.save()
        self.run(scenarios.build(scenarios.pick(text)))
        return self

    def _pending_question(self):
        answered = set(item.get("tool_call_id") for item in self.conversation.messages() if item.get("role") == "tool")
        for message in reversed(self.conversation.messages()):
            for call in message.get("tool_calls") or []:
                if call_name(call) == ask_user.NAME and call.get("id") not in answered:
                    return call.get("id")
        return None

    def wait_confirm(self, call_id, items):
        self.pending_confirm = call_id
        self.emit("confirm", {"call_id": call_id, "tool": "apply_changes", "server": "brim", "items": items})

    def decide(self, decision, comment=""):
        call_id, self.pending_confirm = self.pending_confirm, None
        if call_id is None:
            return
        self.emit("confirmed", {"call_id": call_id, "decision": decision})
        status = "ok" if decision == "approve" else "rejected"
        payload = {"applied": [{"kind": "select_profile"}]} if status == "ok" else {
            "error": {"code": "rejected", "message": comment or "Пользователь отклонил"}}
        self.conversation.append({"role": "tool", "tool_call_id": call_id, "brim_status": status, "brim_server": "brim",
                                  "content": json.dumps(payload, ensure_ascii=False)})
        self.run(scenarios.after_decision(decision))

    def cancel(self):
        self.cancelled = True
        self.conversation.save()
        QTimer.singleShot(0, lambda: self.emit("finished"))
        return True


class ScriptedLoop(object):
    def turn(self, conversation, mode, emit, skill=None):
        return ScriptedTurn(conversation, emit)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if os.environ.get("BRIM_SOFTWARE", "1") == "1":
        os.environ.setdefault("QT_QUICK_BACKEND", "software")
    app = QGuiApplication(sys.argv)
    workdir = tempfile.mkdtemp(prefix="brim-playground-")
    settings = PluginSettings(MemoryStore({"llm_base_url": "http://playground/v1", "llm_model": "playground",
                                           "language": os.environ.get("BRIM_LANG", "ru"),
                                           "theme": os.environ.get("BRIM_THEME", "dark")}))
    service = WorkspaceService(ScenePort(), WorkspaceStore(os.path.join(workdir, "chats")))
    holder = {}

    def build(runner, on_change):
        return ChatPresenter(settings, service, ScriptedLoop(), Llm(), Hub(), runner, on_change,
                             post=lambda function: holder["controller"].post(function), open_path=lambda path: None)

    controller = ChatController(build, settings)
    holder["controller"] = controller
    controller.start()
    engine = QQmlApplicationEngine()
    engine.warnings.connect(lambda items: [print("QML:", item.toString(), flush=True) for item in items])
    engine.rootContext().setContextProperty("brim", controller)
    engine.load(QUrl.fromLocalFile(QML))
    if not engine.rootObjects():
        raise SystemExit("QML failed to load")
    window = sip.cast(engine.rootObjects()[0], QQuickWindow)
    window.setProperty("width", int(os.environ.get("BRIM_WIDTH", "1180")))
    window.setProperty("height", int(os.environ.get("BRIM_HEIGHT", "780")))
    shot = os.environ.get("BRIM_SHOT")
    if shot or os.environ.get("BRIM_HIDDEN") == "1":
        window.setFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowDoesNotAcceptFocus | Qt.WindowTransparentForInput)
        window.setPosition(-6000, -6000)
    window.setProperty("visible", True)
    bridge = WebBridge(controller, workdir, os.path.join(workdir, "uploads"))
    web = WebChatServer(bridge, WEB, port=int(os.environ.get("BRIM_WEB_PORT", "0")))
    controller.add_view_listener(bridge.publish)
    web.start()
    print("Браузерный чат:", web.url(), flush=True)
    print(scenarios.help_text(), flush=True)
    for spec in filter(None, os.environ.get("BRIM_SCRIPT", "").split(";")):
        at, action = spec.split("=", 1)
        QTimer.singleShot(int(at), lambda action=action: run_action(controller, action))
    if shot:
        QTimer.singleShot(int(os.environ.get("BRIM_SHOT_MS", "2000")),
                          lambda: (window.grabWindow().save(shot), app.quit()))
    sys.exit(app.exec_())


def run_action(controller, action):
    name, _, value = action.partition(":")
    if name == "send":
        controller.send(value)
    elif name == "settings":
        language, theme = value.split(",")
        controller.applySettings("http://playground/v1", "playground", "", language, theme)


if __name__ == "__main__":
    main()
