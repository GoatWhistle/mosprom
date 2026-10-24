from .export import prepare_export


class ChatExporter(object):
    def __init__(self, state, settings, store, submit, notice, strings, open_path):
        self.state = state
        self._settings = settings
        self._store = store
        self._submit = submit
        self._notice = notice
        self._strings = strings
        self._open_path = open_path
        self._prepared = None

    def export(self, root, request_capture):
        state = self.state
        strings = self._strings()
        if state.conversation_id is None or not state.messages:
            self._notice(strings["export_empty"])
            return
        if state.running or state.exporting:
            self._notice(strings["busy_run"])
            return
        self._settings.set_export_root(root)
        state.exporting = True
        conversation_id = state.conversation_id
        model = self._settings.llm()["model"]

        def work():
            return prepare_export(root, self._store.load(conversation_id), strings, model)

        def done(prepared):
            self._prepared = prepared
            request_capture(prepared["path"])

        self._submit(work, done, on_error=self._failed)

    def _failed(self, error):
        self.state.exporting = False
        self._notice("%s: %s" % (self._strings()["export_failed"], error))

    def capture_done(self, pages, error):
        prepared, self._prepared = self._prepared, None
        self.state.exporting = False
        if prepared is None:
            return
        strings = self._strings()
        text = strings["export_done"] % (pages, prepared["path"])
        if not prepared["copied"]:
            text += ". " + strings["export_no_slice"]
        if error:
            text += ". %s: %s" % (strings["export_capture_failed"], error)
        self._notice(text)
        self._open_path(prepared["path"])
