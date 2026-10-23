import threading
import uuid

from .protocol import constants
from .protocol.backend_http import BackendHttpError

PREFIX = "brim/"
DEFAULTS = {
    "backend_url": constants.DEFAULT_BACKEND_URL,
    "instance_id": "",
    "token": "",
    "llm_base_url": "",
    "llm_model": "",
    "llm_api_key": "",
    "language": "ru",
    "theme": "dark",
    "mcp_port": 0,
}


class PreferencesStore(object):
    def __init__(self, preferences):
        self._preferences = preferences
        for name, default in DEFAULTS.items():
            preferences.addPreference(PREFIX + name, default)

    def get(self, name):
        return self._preferences.getValue(PREFIX + name)

    def set(self, name, value):
        self._preferences.setValue(PREFIX + name, value)


class MemoryStore(object):
    def __init__(self, values=None):
        self._values = dict(DEFAULTS)
        self._values.update(values or {})

    def get(self, name):
        return self._values[name]

    def set(self, name, value):
        self._values[name] = value


class PluginSettings(object):
    def __init__(self, store):
        self._store = store
        self._registration = threading.RLock()

    def backend_url(self):
        return str(self._store.get("backend_url") or constants.DEFAULT_BACKEND_URL).strip()

    def set_backend_url(self, value):
        value = (value or "").strip().rstrip("/")
        if not value.startswith(("http://", "https://")):
            raise ValueError("backend address must start with http:// or https://")
        if value != self.backend_url():
            self._store.set("token", "")
        self._store.set("backend_url", value)

    def token(self):
        return str(self._store.get("token") or "")

    def instance_id(self):
        value = str(self._store.get("instance_id") or "")
        if not value:
            value = "slicer-" + uuid.uuid4().hex
            self._store.set("instance_id", value)
        return value

    def llm(self):
        return {
            "base_url": str(self._store.get("llm_base_url") or ""),
            "model": str(self._store.get("llm_model") or ""),
            "api_key": str(self._store.get("llm_api_key") or ""),
        }

    def llm_configured(self):
        return all(self.llm().values())

    def set_llm(self, base_url, model, api_key):
        self._store.set("llm_base_url", (base_url or "").strip())
        self._store.set("llm_model", (model or "").strip())
        if api_key:
            self._store.set("llm_api_key", api_key)

    def mcp_port(self):
        return int(self._store.get("mcp_port") or 0)

    def set_mcp_port(self, value):
        self._store.set("mcp_port", int(value))

    def language(self):
        return "en" if self._store.get("language") == "en" else "ru"

    def set_language(self, value):
        self._store.set("language", "en" if value == "en" else "ru")

    def theme(self):
        return "light" if self._store.get("theme") == "light" else "dark"

    def set_theme(self, value):
        self._store.set("theme", "light" if value == "light" else "dark")

    def ensure_registered(self, http_client):
        with self._registration:
            if self.token():
                return self.token()
            for _ in range(3):
                try:
                    reply = http_client.register(self.instance_id())
                except BackendHttpError as error:
                    if error.status == 409:
                        self._store.set("instance_id", "")
                        continue
                    raise
                self._store.set("token", reply["token"])
                return reply["token"]
            raise BackendHttpError("could not register this slicer instance")

    def forget_registration(self):
        with self._registration:
            self._store.set("token", "")


class RegisteredConnection(object):
    def __init__(self, settings):
        self._settings = settings
        self._http = None

    def bind(self, http_client):
        self._http = http_client

    def backend_url(self):
        return self._settings.backend_url()

    def token(self):
        if not self._settings.token():
            self._settings.ensure_registered(self._http)
        return self._settings.token()

    def forget_registration(self):
        self._settings.forget_registration()
