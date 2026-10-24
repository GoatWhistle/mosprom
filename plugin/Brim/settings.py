import json
import re

from .agent.hub import LOCAL_SERVER

PREFIX = "brim/"
DEFAULTS = {
    "llm_base_url": "",
    "llm_model": "",
    "llm_api_key": "",
    "mcp_servers": "[]",
    "risk_ratio": "2",
    "language": "ru",
    "theme": "dark",
    "mcp_port": 0,
    "panel_width": 0,
    "export_root": "",
}
SERVER_NAME = re.compile(r"^[A-Za-z0-9_-]{1,24}$")


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


def parse_header(line):
    line = (line or "").strip()
    if not line:
        return {}
    name, separator, value = line.partition(":")
    if not separator or not name.strip() or not value.strip():
        raise ValueError("header must look like Name: value")
    return {name.strip(): value.strip()}


class PluginSettings(object):
    def __init__(self, store):
        self._store = store

    def llm(self):
        return {
            "base_url": str(self._store.get("llm_base_url") or ""),
            "model": str(self._store.get("llm_model") or ""),
            "api_key": str(self._store.get("llm_api_key") or ""),
        }

    def llm_configured(self):
        llm = self.llm()
        return bool(llm["base_url"] and llm["model"])

    def set_llm(self, base_url, model, api_key):
        base_url = (base_url or "").strip().rstrip("/")
        if base_url and not base_url.startswith(("http://", "https://")):
            raise ValueError("LLM URL must start with http:// or https://")
        self._store.set("llm_base_url", base_url)
        self._store.set("llm_model", (model or "").strip())
        if api_key:
            self._store.set("llm_api_key", api_key)

    def mcp_servers(self):
        try:
            items = json.loads(str(self._store.get("mcp_servers") or "[]"))
        except ValueError:
            return []
        servers = []
        for item in items if isinstance(items, list) else []:
            if isinstance(item, dict) and SERVER_NAME.match(str(item.get("name", ""))) and item.get("url"):
                headers = item.get("headers") if isinstance(item.get("headers"), dict) else {}
                servers.append({"name": item["name"], "url": str(item["url"]),
                                "headers": dict((str(key), str(value)) for key, value in headers.items()),
                                "enabled": item.get("enabled", True) is not False})
        return servers

    def _save_servers(self, servers):
        self._store.set("mcp_servers", json.dumps(servers, ensure_ascii=False))

    def add_mcp_server(self, name, url, header_line):
        name = (name or "").strip()
        url = (url or "").strip()
        if not SERVER_NAME.match(name) or name == LOCAL_SERVER:
            raise ValueError("server name: 1-24 latin letters, digits, _ or -, not %s" % LOCAL_SERVER)
        if not url.startswith(("http://", "https://")):
            raise ValueError("server URL must start with http:// or https://")
        servers = self.mcp_servers()
        if any(item["name"] == name for item in servers):
            raise ValueError("server %s already exists" % name)
        servers.append({"name": name, "url": url, "headers": parse_header(header_line), "enabled": True})
        self._save_servers(servers)

    def set_mcp_server_enabled(self, name, enabled):
        servers = self.mcp_servers()
        for item in servers:
            if item["name"] == name:
                item["enabled"] = bool(enabled)
        self._save_servers(servers)

    def remove_mcp_server(self, name):
        self._save_servers([item for item in self.mcp_servers() if item["name"] != name])

    def risk_ratio(self):
        return self._store.get("risk_ratio")

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

    def panel_width(self):
        return int(self._store.get("panel_width") or 0)

    def set_panel_width(self, value):
        self._store.set("panel_width", max(0, int(value)))

    def export_root(self):
        return str(self._store.get("export_root") or "")

    def set_export_root(self, value):
        self._store.set("export_root", str(value or ""))
