from ..workspace.service import WorkspaceError
from .history import conversation_row


class ProjectSwitching(object):
    def __init__(self, state, workspace, http, submit, notice, strings, history, stop_run):
        self._state = state
        self._workspace = workspace
        self._http = http
        self._submit = submit
        self._notice = notice
        self._strings = strings
        self._history = history
        self._stop_run = stop_run

    def _changed(self):
        self._notice(self._state.notice)

    def enabled(self):
        return self._workspace is not None

    def request(self, target_id=None, create_mode=None, adopt=False):
        state = self._state
        if state.switching is not None:
            self._notice(self._strings()["switching"])
            return
        if state.workspace_blocked:
            self._notice(self._strings()["workspace_blocked"])
            return
        if target_id is not None and target_id == state.conversation_id:
            return
        request = {"target": target_id, "create": create_mode, "adopt": adopt}
        if state.run_working():
            state.switch_prompt = request
            self._changed()
            return
        self._begin(request)

    def cancel_prompt(self):
        self._state.switch_prompt = None
        self._changed()

    def stop_and_switch(self):
        request = self._state.switch_prompt
        if request is None:
            return
        self._state.switch_prompt = None
        self._stop_run(lambda: self._begin(request))

    def retry(self):
        request = self._state.switch_retry
        if request is not None:
            self._state.switch_retry = None
            self.request(request["target"], request["create"], request["adopt"])

    def _begin(self, request):
        state = self._state
        state.switch_retry = None
        state.switching = "saving"
        state.notice = None
        current = state.conversation_id
        self._workspace.lock(True)

        def work():
            if current is not None:
                self._workspace.save(current)

        def done(_):
            self._open(request, current)

        def failed(error):
            self._abort(request, self._strings()["switch_save_failed"], error)

        self._submit(work, done, on_error=failed)
        self._changed()

    def _open(self, request, current):
        state = self._state
        state.switching = "opening"
        mode = state.mode

        def work():
            target = request["target"]
            created = None
            if request["create"] is not None:
                created = self._http.create_conversation_with(request["create"] or mode)
                target = created["id"]
            if request["adopt"]:
                self._workspace.save(target)
                self._workspace.store.set_active(target)
            else:
                self._open_or_restore(current, target)
            return target, created

        def done(result):
            target, created = result
            self._finish(target, created)

        def failed(error):
            if isinstance(error, WorkspaceError) and error.restored is False:
                state.workspace_blocked = True
                state.switching = None
                self._notice(self._strings()["switch_open_blocked"])
                return
            text = self._strings()["switch_open_restored"] if isinstance(error, WorkspaceError) \
                else self._strings()["switch_new_failed"]
            self._abort(request, text, error)

        self._submit(work, done, on_error=failed)
        self._changed()

    def _open_or_restore(self, current, target):
        try:
            self._workspace.open(target)
        except WorkspaceError as failure:
            failure.restored = self._workspace.restore(current)
            raise
        self._workspace.store.set_active(target)

    def _finish(self, target, created):
        state = self._state
        if created is not None:
            state.select_conversation(created["id"], created.get("mode"))
            state.conversations.insert(0, conversation_row(created))
        else:
            self._history.open(target)
        state.workspace_status = self._workspace.store.statuses()
        state.save_state = "saved"
        state.switching = None
        self._workspace.lock(False)
        self._changed()

    def _abort(self, request, text, error):
        state = self._state
        state.switching = None
        state.switch_retry = request
        self._workspace.lock(False)
        self._notice("%s (%s)" % (text, error))

    def recover(self):
        state = self._state
        current = state.conversation_id
        if not state.workspace_blocked or current is None:
            return
        state.switching = "opening"

        def work():
            self._workspace.open(current)

        def done(_):
            state.workspace_blocked = False
            state.switching = None
            self._workspace.lock(False)

        def failed(error):
            state.switching = None
            self._notice("%s (%s)" % (self._strings()["switch_open_blocked"], error))

        self._submit(work, done, on_error=failed)
        self._changed()
