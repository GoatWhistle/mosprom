from ..protocol.backend_http import BackendHttpError
from ..ui.strings import strings_for


class ChatPreferences(object):
    def __init__(self, settings, http, runner, submit, changed, bridge):
        self._settings = settings
        self._http = http
        self._runner = runner
        self._submit = submit
        self._changed = changed
        self._bridge = bridge
        self.notice = None

    def authorized(self, work):
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

    def push_llm(self):
        if self._settings.llm_configured():
            llm = self._settings.llm()
            self._submit(lambda: self._http.put_llm(llm["base_url"], llm["model"], llm["api_key"]))

    def apply(self, backend_url, llm_url, llm_model, llm_key, language, theme):
        try:
            changed_backend = (backend_url or "").strip().rstrip("/") != self._settings.backend_url()
            self._settings.set_backend_url(backend_url)
        except ValueError as error:
            self.notice = str(error)
            self._changed()
            return False
        self._settings.set_llm(llm_url, llm_model, llm_key)
        self._settings.set_language(language)
        self._settings.set_theme(theme)
        self.notice = None
        self.push_llm()
        bridge = self._bridge()
        if changed_backend and bridge is not None:
            bridge.reconnect()
        self._changed()
        return True

    def check(self):
        def finished(value, error):
            self.notice = str(error) if error is not None else strings_for(self._settings.language())["check_ok"]
            self._changed()
        self._runner.submit(self._http.health, finished)
