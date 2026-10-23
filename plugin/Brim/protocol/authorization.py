import json
import threading

from . import constants

READ_ONLY_TOOLS = frozenset((
    constants.TOOL_SEARCH_SETTINGS,
    constants.TOOL_INSPECT_PROFILE,
    constants.TOOL_INSPECT_MATERIAL,
    constants.TOOL_ANALYZE_GEOMETRY,
    constants.TOOL_RENDER_SCENE,
))
MAX_REMEMBERED = 200


def canonical(arguments):
    return json.dumps(arguments or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class AuthorizedCalls(object):
    def __init__(self):
        self._lock = threading.Lock()
        self._calls = {}
        self._order = []

    def register(self, frame):
        call_id = frame.get("call_id")
        if not call_id:
            return
        with self._lock:
            if call_id not in self._calls:
                self._order.append(call_id)
            self._calls[call_id] = frame
            while len(self._order) > MAX_REMEMBERED:
                self._calls.pop(self._order.pop(0), None)

    def match(self, call_id, tool, arguments):
        with self._lock:
            frame = self._calls.get(call_id)
        if frame is None or frame.get("tool") != tool:
            return None
        if canonical(frame.get("arguments")) != canonical(arguments):
            return None
        return frame


class McpAuthorizationGate(object):
    def __init__(self, executor, authorized):
        self._executor = executor
        self._authorized = authorized

    def handle(self, name, arguments, request_id, meta):
        if name in READ_ONLY_TOOLS:
            return self._executor.execute_mcp(name, arguments, request_id)
        frame = self._authorized.match((meta or {}).get("call_id"), name, arguments)
        if frame is None:
            return {
                "ok": False,
                "result": {},
                "error": {
                    "code": "execution_not_authorized",
                    "message": "%s changes the project and runs only for a call authorized by the backend" % name,
                },
                "applied": [],
                "scene_version": None,
            }
        result = self._executor.execute_call(frame)
        return {
            "ok": result.get("ok", False),
            "result": result.get("result", {}),
            "error": result.get("error"),
            "applied": result.get("applied", []),
            "scene_version": result.get("scene_version"),
        }
