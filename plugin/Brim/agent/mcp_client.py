import itertools
import json
import socket
import threading
from urllib import error, request

PROTOCOL_VERSION = "2025-03-26"
CLIENT_INFO = {"name": "brim", "version": "0.3.0"}
DEFAULT_TIMEOUT = 120.0


class McpClientError(Exception):
    pass


def sse_messages(text):
    messages = []
    data = []
    for line in text.splitlines() + [""]:
        if line.startswith(":"):
            continue
        if line == "":
            if data:
                messages.append("\n".join(data))
                data = []
            continue
        field, _, value = line.partition(":")
        if field == "data":
            data.append(value[1:] if value.startswith(" ") else value)
    return messages


def _decode(content_type, raw):
    text = raw.decode("utf-8", "replace")
    if "text/event-stream" in (content_type or ""):
        payloads = sse_messages(text)
    else:
        payloads = [text] if text.strip() else []
    decoded = []
    for payload in payloads:
        try:
            item = json.loads(payload)
        except ValueError:
            raise McpClientError("server sent a message that is not JSON")
        decoded.extend(item if isinstance(item, list) else [item])
    return decoded


class McpHttpClient(object):
    def __init__(self, url, headers=None, timeout=DEFAULT_TIMEOUT, opener=None):
        self._url = url
        self._headers = dict(headers or {})
        self._timeout = timeout
        self._open = opener or request.urlopen
        self._ids = itertools.count(1)
        self._session = None
        self._protocol = PROTOCOL_VERSION
        self._ready = False
        self._lock = threading.Lock()

    def _post(self, message):
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        headers.update(self._headers)
        if self._session:
            headers["Mcp-Session-Id"] = self._session
        if self._ready:
            headers["MCP-Protocol-Version"] = self._protocol
        prepared = request.Request(self._url, data=json.dumps(message).encode("utf-8"), headers=headers, method="POST")
        try:
            with self._open(prepared, timeout=self._timeout) as response:
                session = response.headers.get("Mcp-Session-Id")
                if session:
                    self._session = session
                return response.status, _decode(response.headers.get("Content-Type"), response.read())
        except error.HTTPError as failure:
            return failure.code, None
        except (error.URLError, socket.timeout, OSError) as failure:
            raise McpClientError("server is unreachable: %s" % getattr(failure, "reason", failure))

    def _rpc(self, method, params):
        request_id = next(self._ids)
        status, replies = self._post({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        if status == 404 and self._session:
            raise _SessionExpired()
        if status >= 400 or replies is None:
            raise McpClientError("server returned HTTP %d for %s" % (status, method))
        for reply in replies:
            if isinstance(reply, dict) and reply.get("id") == request_id:
                if "error" in reply:
                    failure = reply["error"] or {}
                    raise McpClientError("%s failed: %s" % (method, failure.get("message", failure)))
                return reply.get("result") or {}
        raise McpClientError("server sent no reply to %s" % method)

    def _initialize(self):
        self._session = None
        self._ready = False
        result = self._rpc("initialize", {"protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                                          "clientInfo": CLIENT_INFO})
        self._protocol = result.get("protocolVersion") or PROTOCOL_VERSION
        self._ready = True
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _call(self, method, params):
        with self._lock:
            if not self._ready:
                self._initialize()
            try:
                return self._rpc(method, params)
            except _SessionExpired:
                self._initialize()
                return self._rpc(method, params)

    def list_tools(self):
        tools = []
        cursor = None
        while True:
            result = self._call("tools/list", {"cursor": cursor} if cursor else {})
            tools.extend(item for item in result.get("tools") or [] if isinstance(item, dict) and item.get("name"))
            cursor = result.get("nextCursor")
            if not cursor:
                return tools

    def call_tool(self, name, arguments):
        return self._call("tools/call", {"name": name, "arguments": arguments})


class _SessionExpired(McpClientError):
    pass
