from ..agent.conversation import Conversation
from ..ui.strings import strings_for
from .autosave import WorkspaceAutosave
from .exporter import ChatExporter
from .files import ChatFiles
from .messaging import ChatMessaging
from .preferences import ChatPreferences
from .state import ChatState
from .switching import ProjectSwitching
from .view import chat_view


class ChatPresenter(object):
    def __init__(self, settings, workspace, loop, llm, hub, runner, on_change, post=None, mcp_port=None,
                 open_path=None, autosave_delay=3.0, skills=None):
        self._settings = settings
        self._workspace = workspace
        self._store = workspace.store
        self._runner = runner
        self._on_change = on_change
        self._post = post or (lambda function: function())
        self._mcp_port = mcp_port
        self._open_path = open_path
        self._skills = skills
        self.state = ChatState()
        self._conversation = None
        self._started = False
        self._preferences = ChatPreferences(settings, runner, self._changed, llm, hub, self._servers_changed)
        self._files = ChatFiles(self.state, self._notice)
        self._messaging = ChatMessaging(self.state, settings, loop, lambda: self._conversation, self._submit,
                                        self._post, self._notice, self._strings, self._changed)
        self._switching = ProjectSwitching(self.state, workspace, self._submit, self._notice, self._strings,
                                           self._select, self._messaging.stop_then, self._messaging.when_idle)
        self._exporter = ChatExporter(self.state, settings, self._store, self._submit, self._notice, self._strings,
                                      self.open_path)
        self._autosave = WorkspaceAutosave(self.state, workspace, self._submit, self._notice, self._strings,
                                           self._post, autosave_delay)

    def view(self):
        return chat_view(self.state, self._settings, self._mcp_port, self._preferences.notice,
                         self._skills.rows() if self._skills is not None else [])

    def _changed(self):
        self._on_change()

    def _notice(self, text):
        self.state.notice = text
        self._changed()

    def _strings(self):
        return strings_for(self._settings.language())

    def _fail(self, error):
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

        self._runner.submit(work, finished)

    def _servers_changed(self, status):
        self.state.servers = status
        self._changed()

    def _persist(self, conversation_id):
        def persist(messages):
            row = self._store.save_messages(conversation_id, messages)
            self._post(lambda: self._row_saved(row))

        return persist

    def _row_saved(self, row):
        self.state.upsert_row(row)
        self._changed()

    def _select(self, conversation_id):
        chat = self._store.load(conversation_id)
        self._conversation = Conversation(conversation_id, chat["messages"], self._persist(conversation_id),
                                          self._store.files_dir(conversation_id))
        self.state.select_conversation(conversation_id, chat.get("mode"), chat["messages"], chat.get("skill"))
        self.state.upsert_row(self._store.row(chat))

    def output_dir(self):
        conversation = self._conversation
        return self._store.output_dir(conversation.id) if conversation is not None else None

    def files_dir(self):
        conversation = self._conversation
        return conversation.files_dir if conversation is not None else None

    def start(self):
        if self._started:
            return
        self._started = True
        self.state.conversations = self._store.chats()
        self.state.workspace_status = self._store.statuses()
        active = self._store.active()
        if active is None and self.state.conversations:
            active = self.state.conversations[0]["id"]
        if active is not None:
            self._restore(active)
        self._preferences.refresh_servers()

    def _restore(self, active):
        self._select(active)
        if self._store.status(active) == "none":
            return
        self.state.switching = "opening"

        def done(_):
            self.state.switching = None
            self.state.save_state = "saved"
            self._workspace.lock(False)

        def failed(error):
            self.state.switching = None
            self.state.workspace_blocked = True
            self._notice("%s (%s)" % (self._strings()["switch_open_blocked"], error))

        self._workspace.lock(True)
        self._submit(self._workspace.restore_active, done, on_error=failed)

    def new_conversation(self, from_scene=False):
        self._switching.request(create_mode=self.state.mode, adopt=from_scene)

    def open_conversation(self, conversation_id):
        if conversation_id != self.state.conversation_id:
            self._switching.request(target_id=conversation_id)

    def _ensure_conversation(self, then):
        mode = self.state.mode
        skill = self.state.skill

        def work():
            row = self._store.create(mode, skill)
            self._store.set_active(row["id"])
            self._workspace.save(row["id"])
            return row

        def done(row):
            kept = (self.state.draft, list(self.state.attachments))
            self._select(row["id"])
            self.state.draft, self.state.attachments = kept
            self.state.workspace_status = self._store.statuses()
            then()

        self._submit(work, done, busy=True)

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

    def on_progress(self, stage, fraction):
        self._messaging.on_progress(stage, fraction)

    def flush_workspace(self):
        self._autosave.flush()

    def attach(self, path):
        self._files.attach(path)

    def remove_attachment(self, index):
        if 0 <= index < len(self.state.attachments):
            del self.state.attachments[index]
            self._changed()

    def set_mode(self, mode):
        if mode not in ("auto", "ask"):
            return
        self.state.mode = mode
        conversation_id = self.state.conversation_id
        if conversation_id is not None:
            self._row_saved(self._store.set_mode(conversation_id, mode))
        self._changed()

    def set_skill(self, skill):
        skill = skill or None
        if skill is not None and (self._skills is None or skill not in self._skills.names()):
            return
        self.state.skill = skill
        conversation_id = self.state.conversation_id
        if conversation_id is not None:
            self._row_saved(self._store.set_skill(conversation_id, skill))
        self._changed()

    def send(self, text):
        self._messaging.send(text, self._ensure_conversation)

    def confirm(self, decision, comment=None):
        self._messaging.confirm(decision, comment)

    def stop(self):
        self._messaging.stop()

    def open_folder(self):
        folder = self.output_dir()
        if folder is not None and self._open_path is not None:
            self._open_path(folder)

    def open_path(self, path):
        if path and self._open_path is not None:
            self._open_path(path)

    def export(self, root, request_capture):
        self._exporter.export(root, request_capture)

    def capture_done(self, pages, error):
        self._exporter.capture_done(pages, error)

    def apply_settings(self, llm_url, llm_model, llm_key, language, theme):
        return self._preferences.apply(llm_url, llm_model, llm_key, language, theme)

    def set_interface(self, language, theme):
        self._preferences.set_interface(language, theme)

    def add_server(self, name, url, header):
        return self._preferences.add_server(name, url, header)

    def toggle_server(self, name, enabled):
        self._preferences.toggle_server(name, enabled)

    def remove_server(self, name):
        self._preferences.remove_server(name)

    def check_connection(self):
        self._preferences.check()
