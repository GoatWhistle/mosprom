import base64
import json
import re
import threading

from .mcp_client import McpClientError

LOCAL_SERVER = "brim"
NAME_LIMIT = 64
UNSAFE_NAME = re.compile(r"[^a-zA-Z0-9_-]")


def model_name(server, tool):
    if server == LOCAL_SERVER:
        return tool
    return UNSAFE_NAME.sub("_", "%s__%s" % (server, tool))[:NAME_LIMIT]


def tool_output(result):
    texts = []
    images = []
    for block in result.get("content") or []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            texts.append(str(block.get("text", "")))
        elif block.get("type") == "image" and block.get("data"):
            try:
                images.append({"mime_type": block.get("mimeType") or "image/png",
                               "data": base64.b64decode(block["data"])})
            except (TypeError, ValueError):
                texts.append("[an image the server returned could not be decoded]")
        else:
            texts.append(json.dumps(block, ensure_ascii=False))
    if not texts and result.get("structuredContent") is not None:
        texts.append(json.dumps(result["structuredContent"], ensure_ascii=False))
    return {"text": "\n".join(texts), "images": images, "is_error": bool(result.get("isError"))}


class LocalServer(object):
    def __init__(self, dispatcher):
        self._dispatcher = dispatcher

    def _rpc(self, method, params):
        reply = self._dispatcher.handle({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
        if "error" in reply:
            raise McpClientError(reply["error"].get("message", "local server failed"))
        return reply["result"]

    def list_tools(self):
        return self._rpc("tools/list", {})["tools"]

    def call_tool(self, name, arguments):
        return self._rpc("tools/call", {"name": name, "arguments": arguments})


class McpHub(object):
    def __init__(self, local_dispatcher, servers, client_factory):
        self._local = LocalServer(local_dispatcher)
        self._servers = servers
        self._client_factory = client_factory
        self._clients = {}
        self._routes = {}
        self._tools = []
        self._status = {}
        self._lock = threading.Lock()

    def _client(self, server):
        key = (server["name"], server["url"], json.dumps(server.get("headers") or {}, sort_keys=True))
        client = self._clients.get(key)
        if client is None:
            client = self._client_factory(server["url"], server.get("headers") or {})
            self._clients = dict((item, value) for item, value in self._clients.items() if item[0] != server["name"])
            self._clients[key] = client
        return client

    def refresh(self):
        tools = []
        routes = {}
        status = {}
        warnings = []
        sources = [(LOCAL_SERVER, self._local)]
        for server in self._servers():
            if not server.get("enabled", True):
                status[server["name"]] = {"state": "off", "tools": 0, "error": None}
                continue
            sources.append((server["name"], self._client(server)))
        for name, client in sources:
            try:
                listed = client.list_tools()
            except Exception as failure:
                if name == LOCAL_SERVER:
                    raise
                status[name] = {"state": "error", "tools": 0, "error": str(failure)}
                warnings.append((name, str(failure)))
                continue
            count = 0
            for tool in listed:
                exposed = model_name(name, tool["name"])
                if exposed in routes:
                    warnings.append((name, "tool %s clashes with another tool and is hidden" % tool["name"]))
                    continue
                routes[exposed] = (name, client, tool)
                tools.append({"name": exposed, "server": name, "tool": tool["name"],
                              "description": tool.get("description") or "",
                              "parameters": tool.get("inputSchema") or {"type": "object", "properties": {}},
                              "annotations": tool.get("annotations") or {}})
                count += 1
            status[name] = {"state": "ok", "tools": count, "error": None}
        with self._lock:
            self._tools = tools
            self._routes = routes
            self._status = status
        return warnings

    def tools(self):
        with self._lock:
            return list(self._tools)

    def describe(self, exposed):
        with self._lock:
            route = self._routes.get(exposed)
        if route is None:
            return None
        server, _, tool = route
        return {"server": server, "tool": tool["name"], "annotations": tool.get("annotations") or {}}

    def status(self):
        with self._lock:
            return dict(self._status)

    def call(self, exposed, arguments):
        with self._lock:
            route = self._routes.get(exposed)
        if route is None:
            return {"text": json.dumps({"ok": False, "error": {"code": "unknown_tool", "message": "no tool %s" % exposed}}),
                    "images": [], "is_error": True, "server": None}
        server, client, tool = route
        try:
            result = client.call_tool(tool["name"], arguments)
        except Exception as failure:
            message = {"ok": False, "error": {"code": "mcp_server_failed", "message": "%s: %s" % (server, failure)}}
            return {"text": json.dumps(message, ensure_ascii=False), "images": [], "is_error": True, "server": server}
        output = tool_output(result)
        output["server"] = server
        return output
