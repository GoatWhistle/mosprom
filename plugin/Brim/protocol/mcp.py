import base64
import json

from . import constants

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


def _error(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


class McpDispatcher(object):
    def __init__(self, tools, call_handler):
        self._tools = list(tools)
        self._names = set(tool["name"] for tool in self._tools)
        self._call_handler = call_handler

    def handle_text(self, text):
        try:
            if isinstance(text, bytes):
                text = text.decode("utf-8")
            request = json.loads(text)
        except ValueError:
            return _error(None, PARSE_ERROR, "parse error")
        if isinstance(request, list):
            responses = [self.handle(item) for item in request]
            responses = [item for item in responses if item is not None]
            return responses or None
        return self.handle(request)

    def handle(self, request):
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0" or "method" not in request:
            return _error(request.get("id") if isinstance(request, dict) else None, INVALID_REQUEST, "invalid request")
        request_id = request.get("id")
        is_notification = "id" not in request
        method = request["method"]
        params = request.get("params") or {}
        if not isinstance(params, dict):
            return None if is_notification else _error(request_id, INVALID_PARAMS, "params must be an object")
        if method.startswith("notifications/"):
            return None
        if is_notification:
            return None
        if method == "initialize":
            return self._ok(request_id, {
                "protocolVersion": constants.MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": constants.SERVER_NAME, "version": constants.SERVER_VERSION},
            })
        if method == "ping":
            return None if is_notification else self._ok(request_id, {})
        if method == "tools/list":
            return self._ok(request_id, {"tools": self._tools})
        if method == "tools/call":
            return self._call(request_id, params)
        if is_notification:
            return None
        return _error(request_id, METHOD_NOT_FOUND, "method not found: %s" % method)

    def _ok(self, request_id, result):
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def _call(self, request_id, params):
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name not in self._names:
            return _error(request_id, INVALID_PARAMS, "unknown tool: %s" % name)
        if not isinstance(arguments, dict):
            return _error(request_id, INVALID_PARAMS, "arguments must be an object")
        try:
            outcome = self._call_handler(name, arguments)
        except Exception as error:
            return _error(request_id, INTERNAL_ERROR, "tool failure: %s" % error)
        payload = {"ok": outcome["ok"], "result": outcome.get("result", {}), "error": outcome.get("error"),
                   "applied": outcome.get("applied", [])}
        content = [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}]
        for image in outcome.get("images") or []:
            content.append({"type": "image", "mimeType": image["mime_type"],
                            "data": base64.b64encode(image["data"]).decode("ascii")})
        return self._ok(request_id, {"content": content, "isError": not outcome["ok"]})
