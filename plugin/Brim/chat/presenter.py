from ..protocol.backend_http import BackendHttpError
from ..ui.strings import strings_for
from .state import ChatState
from .view import chat_view
from .files import ChatFiles
from .history import ChatHistory, conversation_row
from .preferences import ChatPreferences

class ChatPresenter(object):
    def __init__(self, http, settings, runner, on_change, bridge=None, mcp_port=None, cache_dir=None):
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

    def _submit(self, work, done=None, busy=False):
        if busy:
            self.state.busy = True
            self._changed()

        def finished(value, error):
            if busy:
                self.state.busy = False
            if error is not None:
                self._fail(error)
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
        self.refresh_conversations(select_latest=True)

    def _push_llm(self):
        self._preferences.push_llm()

    def refresh_conversations(self, select_latest=False):
        self._history.refresh(select_latest)

    def new_conversation(self):
        mode = self.state.mode

        def work():
            return self._http.create_conversation_with(mode)

        def done(created):
            self.state.select_conversation(created["id"], created.get("mode"))
            self.state.conversations.insert(0, conversation_row(created))

        self._submit(work, done, busy=True)

    def open_conversation(self, conversation_id):
        self._history.open(conversation_id)

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
        text = (text or "").strip()
        pending = self.state.pending
        if pending is not None and pending["type"] == "confirmation":
            if text:
                self.confirm("clarify", text)
            else:
                self._notice(self._strings()["clarify_hint"])
            return
        if not text and not self.state.attachments:
            return
        if self.state.run_active() and self.state.run_state != "awaiting_user" and (pending is None or pending["type"] != "question"):
            self._notice(self._strings()["busy_run"])
            return
        if not self._settings.llm_configured():
            self._notice(self._strings()["llm_missing"])
            return
        if self.state.conversation_id is None:
            self._create_then_send(text)
            return
        self._post_message(self.state.conversation_id, text)

    def _create_then_send(self, text):
        mode = self.state.mode

        def work():
            return self._http.create_conversation_with(mode)

        def done(created):
            kept = list(self.state.attachments)
            self.state.select_conversation(created["id"], created.get("mode"))
            self.state.attachments = kept
            self.state.conversations.insert(0, conversation_row(created))
            self._post_message(created["id"], text)

        self._submit(work, done, busy=True)

    def _post_message(self, conversation_id, text):
        attachments = list(self.state.attachments)
        ids = [item["id"] for item in attachments]
        mode = self.state.mode

        def work():
            return self._http.send_message(conversation_id, text, ids, mode)

        def done(reply):
            self.state.add_sent_message(reply.get("message_id"), reply.get("run_id"), text,
                                        [item["name"] for item in attachments])

        self._submit(work, done, busy=True)

    def confirm(self, decision, text=None):
        run_id = self.state.run_id
        pending = self.state.pending
        if run_id is None or pending is None or pending["type"] != "confirmation":
            return
        if decision == "clarify" and not (text or "").strip():
            self._notice(self._strings()["clarify_hint"])
            return

        def work():
            return self._http.confirm(run_id, decision, text)

        def done(_):
            if self.state.pending is not None and self.state.pending.get("batch_id") == pending.get("batch_id"):
                self.state.resolve_confirmation(decision)

        self._submit(work, done, busy=True)

    def stop(self):
        run_id = self.state.run_id
        if run_id is None or not self.state.run_active():
            return
        bridge = self._bridge

        def work():
            reply = self._http.stop_run(run_id)
            return reply

        def done(_):
            self.state.mark_stopped()
            self.state.run_state = "aborted"
            if bridge is not None:
                bridge.cancel_run(run_id)

        self._submit(work, done, busy=True)

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
