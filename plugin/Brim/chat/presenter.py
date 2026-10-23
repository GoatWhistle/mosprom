from ..protocol.backend_http import BackendHttpError
from ..ui.strings import strings_for
from .state import ChatState
from .view import chat_view
from .files import ChatFiles
from .history import ChatHistory, conversation_row
from .preferences import ChatPreferences
from .autosave import WorkspaceAutosave
from .switching import ProjectSwitching
from .messaging import ChatMessaging

class ChatPresenter(object):
    def __init__(self, http, settings, runner, on_change, bridge=None, mcp_port=None, cache_dir=None,
                 workspace=None, post=None, autosave_delay=3.0):
        self._http = http
        self._settings = settings
        self._runner = runner
        self._on_change = on_change
        self._bridge = bridge
        self._mcp_port = mcp_port
        self._cache_dir = cache_dir
        self.state = ChatState()
        self._started = False
        self._preferences = ChatPreferences(settings, http, runner, self._submit, self._changed, lambda: self._bridge)
        self._files = ChatFiles(self.state, http, self._submit, self._notice, self._strings)
        self._history = ChatHistory(self.state, http, self._submit)
        self._messaging = ChatMessaging(self.state, http, settings, self._submit, self._notice, self._strings,
                                        lambda: self._bridge)
        self._workspace = workspace
        self._switching = ProjectSwitching(self.state, workspace, http, self._submit, self._notice,
                                           self._strings, self._history, self._messaging.stop_then)
        self._autosave = WorkspaceAutosave(self.state, workspace, self._submit, self._notice, self._strings,
                                           post or (lambda function: function()), autosave_delay)

    def attach_bridge(self, bridge):
        self._bridge = bridge

    def view(self):
        return chat_view(self.state, self._settings, self._mcp_port, self._preferences.notice)

    def _changed(self):
        self._on_change()

    def _notice(self, text):
        self.state.notice = text
        self._changed()

    def _fail(self, error):
        if isinstance(error, BackendHttpError):
            self._notice(str(error))
        else:
            self._notice("%s: %s" % (type(error).__name__, error))

    def _submit(self, work, done=None, busy=False, on_error=None):
        if busy:
            self.state.busy = True
            self._changed()

        def finished(value, error):
            if busy:
                self.state.busy = False
            if error is not None:
                (on_error or self._fail)(error)
            elif done is not None:
                done(value)
            self._changed()

        self._runner.submit(self._with_auth(work), finished)

    def _with_auth(self, work):
        return self._preferences.authorized(work)

    def start(self):
        if self._started:
            return
        self._started = True
        self._push_llm()
        self._restore_workspace()
        self.refresh_conversations(select_latest=True)

    def _restore_workspace(self):
        if self._workspace is None:
            return
        store = self._workspace.store
        self.state.workspace_status = store.statuses()
        active = store.active()
        if active is None or store.status(active) == "none":
            return
        self.state.select_conversation(active, None)
        self.state.switching = "opening"

        def work():
            return self._workspace.restore_active()

        def done(_):
            self.state.switching = None
            self.state.save_state = "saved"
            self._workspace.lock(False)

        def failed(error):
            self.state.switching = None
            self.state.workspace_blocked = True
            self._notice("%s (%s)" % (self._strings()["switch_open_blocked"], error))

        self._workspace.lock(True)
        self._submit(work, done, on_error=failed)

    def _push_llm(self):
        self._preferences.push_llm()

    def refresh_conversations(self, select_latest=False):
        self._history.refresh(select_latest)

    def new_conversation(self, from_scene=False):
        mode = self.state.mode
        if self._switching.enabled():
            self._switching.request(create_mode=mode, adopt=from_scene)
            return

        def work():
            return self._http.create_conversation_with(mode)

        def done(created):
            self.state.select_conversation(created["id"], created.get("mode"))
            self.state.conversations.insert(0, conversation_row(created))

        self._submit(work, done, busy=True)

    def open_conversation(self, conversation_id):
        if self._switching.enabled() and conversation_id != self.state.conversation_id:
            self._switching.request(target_id=conversation_id)
            return
        self._history.open(conversation_id)

    def cancel_switch(self):
        self._switching.cancel_prompt()

    def stop_and_switch(self):
        self._switching.stop_and_switch()

    def retry_switch(self):
        self._switching.retry()

    def recover_workspace(self):
        self._switching.recover()

    def set_draft(self, text):
        self.state.set_draft(text)

    def on_scene_changed(self):
        self._autosave.changed()

    def flush_workspace(self):
        self._autosave.flush()

    def reload_history(self):
        self._history.reload()

    def attach(self, path):
        self._files.attach(path)

    def remove_attachment(self, index):
        if 0 <= index < len(self.state.attachments):
            del self.state.attachments[index]
            self._changed()

    def set_mode(self, mode):
        if mode not in ("auto", "ask"):
            return
        previous = self.state.mode
        self.state.mode = mode
        self._changed()
        conversation_id = self.state.conversation_id
        if conversation_id is None:
            return

        def work():
            return self._http.set_mode(conversation_id, mode)

        def finished(value, error):
            if error is not None:
                self.state.mode = previous
                self._fail(error)
            self._changed()

        self._runner.submit(self._with_auth(work), finished)

    def send(self, text):
        self._messaging.send(text)

    def confirm(self, decision, text=None):
        self._messaging.confirm(decision, text)

    def stop(self):
        self._messaging.stop()

    def save_artifact(self, kind, destination):
        self._files.save(kind, destination)

    def apply_settings(self, backend_url, llm_url, llm_model, llm_key, language, theme):
        return self._preferences.apply(backend_url, llm_url, llm_model, llm_key, language, theme)

    def check_backend(self):
        self._preferences.check()

    def on_chat_event(self, frame):
        self._history.record(frame)
        if self.state.apply_chat_event(frame):
            self._changed()
            if frame.get("event") == "run_state" and (frame.get("payload") or {}).get("state") == "completed":
                self.reload_history()

    def on_progress(self, frame):
        self.state.apply_progress(frame)
        self._changed()

    def on_tool_result(self, frame, tool):
        self.state.apply_tool_result(frame, tool)
        self._changed()

    def on_status(self, status):
        previous = self.state.connection
        if status == "connected":
            self.state.connection = "connected"
        elif status == "disconnected" or status.startswith("error"):
            self.state.connection = "disconnected"
        else:
            return
        self._changed()
        if status == "connected" and previous != "connected" and self._started:
            self._push_llm()
            self.reload_history()

    def _strings(self):
        return strings_for(self._settings.language())
