class WorkspaceError(Exception):
    def __init__(self, phase, cause, restored=None):
        Exception.__init__(self, "%s: %s" % (phase, cause))
        self.phase = phase
        self.cause = cause
        self.restored = restored


class WorkspaceService(object):
    def __init__(self, port, store):
        self._port = port
        self._store = store

    @property
    def store(self):
        return self._store

    def save(self, conversation_id):
        if self._port.scene_is_empty():
            self._store.mark_empty(conversation_id)
            return "empty"
        path = self._store.temp_path(conversation_id)
        try:
            self._port.save_workspace(path)
            self._store.commit(conversation_id)
        except Exception as error:
            self._store.discard_temp(conversation_id)
            raise WorkspaceError("save", error)
        return "saved"

    def open(self, conversation_id):
        status = self._store.status(conversation_id)
        try:
            if status == "saved":
                self._port.load_workspace(self._store.path_for(conversation_id))
            else:
                self._port.clear_workspace()
                if status == "none":
                    self._store.mark_empty(conversation_id)
        except Exception as error:
            raise WorkspaceError("open", error)

    def lock(self, locked):
        self._port.lock_changes(locked)

    def restore(self, conversation_id):
        return self._restore(conversation_id)

    def _restore(self, conversation_id):
        if conversation_id is None:
            return True
        try:
            self.open(conversation_id)
        except WorkspaceError:
            return False
        return True

    def restore_active(self):
        active = self._store.active()
        if active is None or self._store.status(active) == "none":
            return None
        self._port.lock_changes(True)
        try:
            self.open(active)
        finally:
            self._port.lock_changes(False)
        return active
