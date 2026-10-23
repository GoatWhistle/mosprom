from ..workspace.autosave import Debouncer


class WorkspaceAutosave(object):
    def __init__(self, state, workspace, submit, notice, strings, post, delay):
        self._state = state
        self._workspace = workspace
        self._submit = submit
        self._notice = notice
        self._strings = strings
        self._debounce = Debouncer(delay, self.save_now, post) if workspace is not None else None

    def _changed(self):
        self._notice(self._state.notice)

    def changed(self):
        state = self._state
        if self._debounce is None or state.conversation_id is None:
            return
        if state.switching is not None or state.workspace_blocked:
            return
        state.save_state = "dirty"
        self._debounce.trigger()
        self._changed()

    def save_now(self):
        state = self._state
        conversation_id = state.conversation_id
        if conversation_id is None or state.switching is not None or state.workspace_blocked:
            return
        state.save_state = "saving"

        def work():
            return self._workspace.save(conversation_id)

        def done(status):
            state.workspace_status[conversation_id] = status
            if state.conversation_id == conversation_id and state.save_state == "saving":
                state.save_state = "saved"

        def failed(error):
            if state.conversation_id == conversation_id:
                state.save_state = "failed"
            self._notice("%s: %s" % (self._strings()["save_failed"], error))

        self._submit(work, done, on_error=failed)
        self._changed()

    def flush(self):
        state = self._state
        if self._debounce is None or state.conversation_id is None or state.save_state != "dirty":
            return
        self._debounce.cancel()
        self._workspace.save(state.conversation_id)
        state.save_state = "saved"
