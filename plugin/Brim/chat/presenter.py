import os

from ..execution.operations import MODEL_EXTENSIONS
from ..protocol.backend_http import BackendHttpError
from ..ui.strings import strings_for
from .state import ChatState

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")
ATTACHMENT_EXTENSIONS = IMAGE_EXTENSIONS + MODEL_EXTENSIONS
MAX_ATTACHMENT_BYTES = 100 * 1024 * 1024
MAX_ATTACHMENTS = 8


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
        self._settings_notice = None

    def attach_bridge(self, bridge):
        self._bridge = bridge

    def view(self):
        snapshot = self.state.snapshot()
        strings = strings_for(self._settings.language())
        llm = self._settings.llm()
        snapshot.update({
            "t": strings,
            "language": self._settings.language(),
            "theme": self._settings.theme(),
            "settings": {
                "backend_url": self._settings.backend_url(),
                "llm_base_url": llm["base_url"],
                "llm_model": llm["model"],
                "llm_key_saved": bool(llm["api_key"]),
            },
            "settings_notice": self._settings_notice,
            "mcp_port": self._mcp_port() if callable(self._mcp_port) else self._mcp_port,
        })
        return snapshot

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
        def run():
            try:
                self._settings.ensure_registered(self._http)
                return work()
            except BackendHttpError as error:
                if error.status != 401:
                    raise
                self._settings.forget_registration()
                self._settings.ensure_registered(self._http)
                if self._settings.llm_configured():
                    llm = self._settings.llm()
                    self._http.put_llm(llm["base_url"], llm["model"], llm["api_key"])
                return work()

        return run

    def start(self):
        if self._started:
            return
        self._started = True
        self._push_llm()
        self.refresh_conversations(select_latest=True)

    def _push_llm(self):
        if not self._settings.llm_configured():
            return
        llm = self._settings.llm()
        self._submit(lambda: self._http.put_llm(llm["base_url"], llm["model"], llm["api_key"]))

    def refresh_conversations(self, select_latest=False):
        def work():
            return self._http.list_conversations()

        def done(page):
            self.state.conversations = [self._conversation_row(item) for item in page.get("items", [])]
            if select_latest and self.state.conversation_id is None and self.state.conversations:
                self.open_conversation(self.state.conversations[0]["id"])

        self._submit(work, done)

    def _conversation_row(self, item):
        return {"id": item["id"], "title": item.get("title") or "", "mode": item.get("mode", "ask"),
                "updated_at": str(item.get("updated_at", ""))}

    def new_conversation(self):
        mode = self.state.mode

        def work():
            return self._http.create_conversation_with(mode)

        def done(created):
            self.state.select_conversation(created["id"], created.get("mode"))
            self.state.conversations.insert(0, self._conversation_row(created))

        self._submit(work, done, busy=True)

    def open_conversation(self, conversation_id):
        def work():
            return self._http.get_conversation(conversation_id)

        def done(detail):
            if self.state.conversation_id != conversation_id:
                self.state.select_conversation(conversation_id, detail["conversation"].get("mode"))
            self.state.load_history(detail)

        self._submit(work, done, busy=True)

    def reload_history(self):
        conversation_id = self.state.conversation_id
        if conversation_id is None:
            self.refresh_conversations(select_latest=True)
            return

        def done(detail):
            self.state.load_history(detail)

        self._submit(lambda: self._http.get_conversation(conversation_id), done)

    def attach(self, path):
        path = str(path)
        name = os.path.basename(path)
        if os.path.splitext(name)[1].lower() not in ATTACHMENT_EXTENSIONS:
            self._notice("%s: JPG, PNG, STL, OBJ, 3MF" % name)
            return
        if len(self.state.attachments) >= MAX_ATTACHMENTS:
            self._notice("max %d" % MAX_ATTACHMENTS)
            return
        try:
            size = os.path.getsize(path)
        except OSError as error:
            self._notice(str(error))
            return
        if size > MAX_ATTACHMENT_BYTES:
            self._notice("%s: %d MiB" % (name, size // (1024 * 1024)))
            return

        def work():
            with open(path, "rb") as handle:
                return self._http.upload_attachment(name, handle.read())

        def done(meta):
            self.state.attachments.append({"id": meta["id"], "name": meta.get("name", name), "size": meta.get("size", size)})

        self._submit(work, done, busy=True)

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
        if self.state.run_active() and (pending is None or pending["type"] != "question"):
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
            self.state.conversations.insert(0, self._conversation_row(created))
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
        run_id = (self.state.result or {}).get("run_id") or self.state.run_id
        if run_id is None:
            return

        def work():
            payload, _ = self._http.download_artifact(run_id, kind)
            with open(destination, "wb") as handle:
                handle.write(payload)
            return destination

        def done(path):
            self.state.notice = "%s: %s" % (self._strings()["saved"], path)

        self._submit(work, done, busy=True)

    def apply_settings(self, backend_url, llm_url, llm_model, llm_key, language, theme):
        try:
            changed_backend = (backend_url or "").strip().rstrip("/") != self._settings.backend_url()
            self._settings.set_backend_url(backend_url)
        except ValueError as error:
            self._settings_notice = str(error)
            self._changed()
            return False
        self._settings.set_llm(llm_url, llm_model, llm_key)
        self._settings.set_language(language)
        self._settings.set_theme(theme)
        self._settings_notice = None
        if self._settings.llm_configured() or changed_backend:
            self._push_llm()
        if changed_backend and self._bridge is not None:
            self._bridge.reconnect()
        self._changed()
        return True

    def check_backend(self):
        def done(_):
            self._settings_notice = self._strings()["check_ok"]

        def finished(value, error):
            if error is not None:
                self._settings_notice = str(error)
            else:
                done(value)
            self._changed()

        self._runner.submit(self._http.health, finished)

    def on_chat_event(self, frame):
        if self.state.apply_chat_event(frame):
            self._changed()

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
            self.reload_history()

    def _strings(self):
        return strings_for(self._settings.language())
