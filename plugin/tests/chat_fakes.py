import os
import tempfile
import zipfile

from Brim.chat.presenter import ChatPresenter
from Brim.settings import MemoryStore, PluginSettings
from Brim.slicer.project_archive import verify_workspace
from Brim.ui.runner import ImmediateRunner
from Brim.workspace.service import WorkspaceService
from Brim.workspace.store import WorkspaceStore


class WorkspacePort(object):
    def __init__(self):
        self.scene = []
        self.locked = False
        self.lock_log = []
        self.fail_save = False
        self.fail_load = False

    def lock_changes(self, locked):
        self.locked = locked
        self.lock_log.append(locked)

    def scene_is_empty(self):
        return not self.scene

    def save_workspace(self, path):
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("3D/3dmodel.model", "<model>%s</model>" % ",".join(self.scene))
        if self.fail_save:
            with open(path, "wb") as handle:
                handle.write(b"torn")
            raise IOError("disk full")

    def load_workspace(self, path):
        verify_workspace(path)
        if self.fail_load:
            raise IOError("loader crashed")
        with zipfile.ZipFile(path) as archive:
            text = archive.read("3D/3dmodel.model").decode("utf-8")[7:-8]
        self.scene = [item for item in text.split(",") if item]

    def clear_workspace(self):
        self.scene = []


class FakeTurn(object):
    def __init__(self, loop, conversation, mode, emit):
        self.loop = loop
        self.conversation = conversation
        self.mode = mode
        self.emit_to = emit
        self.started = None
        self.decisions = []
        self.cancelled = False
        self.release_on_cancel = True

    def start(self, text=None, attachments=None, answer=None):
        self.started = {"text": text, "attachments": attachments, "answer": answer}
        if text is not None or attachments:
            self.conversation.append({"role": "user", "content": text or "", "brim_attachments": attachments or []})
        self.loop.turns.append(self)
        return self

    def emit(self, kind, payload=None):
        self.emit_to(self, kind, payload or {})

    def decide(self, decision, comment=""):
        self.decisions.append((decision, comment))

    def cancel(self):
        self.cancelled = True
        return self.release_on_cancel


class FakeLoop(object):
    def __init__(self):
        self.turns = []

    def turn(self, conversation, mode, emit, skill=None):
        return FakeTurn(self, conversation, mode, emit)


class FakeHub(object):
    def __init__(self):
        self.refreshed = 0

    def refresh(self):
        self.refreshed += 1
        return []

    def status(self):
        return {"brim": {"state": "ok", "tools": 8, "error": None}}


class FakeLlm(object):
    def models(self):
        return ["m"]


def make_settings(**values):
    base = {"llm_base_url": "https://l/v1", "llm_model": "m", "llm_api_key": "k"}
    base.update(values)
    return PluginSettings(MemoryStore(base))


def build(settings=None, port=None, store=None):
    directory = tempfile.mkdtemp()
    port = port or WorkspacePort()
    store = store or WorkspaceStore(os.path.join(directory, "chats"))
    service = WorkspaceService(port, store)
    loop = FakeLoop()
    opened = []
    presenter = ChatPresenter(settings or make_settings(), service, loop, FakeLlm(), FakeHub(), ImmediateRunner(),
                              lambda: None, open_path=opened.append)
    presenter.opened = opened
    presenter.loop = loop
    return presenter, port, store


def two_projects():
    presenter, port, store = build()
    presenter.start()
    presenter.new_conversation()
    first = presenter.state.conversation_id
    port.scene = ["bracket"]
    presenter.new_conversation()
    return presenter, port, store, first, presenter.state.conversation_id
