from ..ui.strings import strings_for


class ChatPreferences(object):
    def __init__(self, settings, runner, changed, llm, hub, servers_changed):
        self._settings = settings
        self._runner = runner
        self._changed = changed
        self._llm = llm
        self._hub = hub
        self._servers_changed = servers_changed
        self.notice = None

    def _strings(self):
        return strings_for(self._settings.language())

    def _report(self, text):
        self.notice = text
        self._changed()

    def apply(self, llm_url, llm_model, llm_key, language, theme):
        try:
            self._settings.set_llm(llm_url, llm_model, llm_key)
        except ValueError as error:
            self._report(str(error))
            return False
        self._settings.set_language(language)
        self._settings.set_theme(theme)
        self._report(None)
        return True

    def set_interface(self, language, theme):
        self._settings.set_language(language)
        self._settings.set_theme(theme)
        self._changed()

    def add_server(self, name, url, header):
        try:
            self._settings.add_mcp_server(name, url, header)
        except ValueError as error:
            self._report(str(error))
            return False
        self._report(None)
        self.refresh_servers()
        return True

    def toggle_server(self, name, enabled):
        self._settings.set_mcp_server_enabled(name, enabled)
        self.refresh_servers()

    def remove_server(self, name):
        self._settings.remove_mcp_server(name)
        self.refresh_servers()

    def refresh_servers(self):
        def finished(warnings, error):
            if error is not None:
                self.notice = str(error)
            self._servers_changed(self._hub.status())

        self._runner.submit(self._hub.refresh, finished)

    def check(self):
        strings = self._strings()

        def work():
            models = self._llm.models()
            warnings = self._hub.refresh()
            return models, warnings

        def finished(value, error):
            if error is not None:
                self.notice = "%s: %s" % (strings["check_failed"], error)
            else:
                models, warnings = value
                lines = [strings["check_ok"] + (" (%d)" % len(models) if models else "")]
                lines.extend("MCP %s: %s" % item for item in warnings)
                self.notice = "\n".join(lines)
            self._servers_changed(self._hub.status())

        self._runner.submit(work, finished)
