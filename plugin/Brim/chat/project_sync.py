from ..protocol.backend_http import BackendHttpError


class ProjectSync(object):
    def __init__(self, workspace, http):
        self._workspace = workspace
        self._http = http
        self.link_failed = False

    def save(self, conversation_id, activate):
        status = self._workspace.save(conversation_id)
        version = None
        try:
            project = self._http.put_project(conversation_id, status,
                                             self._workspace.store.digest(conversation_id), activate)
            version = (project.get("project") or {}).get("version")
            self.link_failed = False
        except BackendHttpError:
            self.link_failed = True
        return status, version

    def activate(self, conversation_id):
        try:
            self._http.activate_conversation(conversation_id)
            self.link_failed = False
        except BackendHttpError:
            self.link_failed = True
