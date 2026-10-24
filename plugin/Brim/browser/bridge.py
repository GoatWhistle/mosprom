import json
import os
import threading
import uuid

from ..chat.files import safe_name

ACTIONS = {
    "send": ("send", (str,)),
    "newChat": ("newChat", ()),
    "openChat": ("openChat", (str,)),
    "newChatFromScene": ("newChatFromScene", ()),
    "setDraft": ("setDraft", (str,)),
    "cancelSwitch": ("cancelSwitch", ()),
    "stopAndSwitch": ("stopAndSwitch", ()),
    "retrySwitch": ("retrySwitch", ()),
    "recoverWorkspace": ("recoverWorkspace", ()),
    "setMode": ("setMode", (str,)),
    "setSkill": ("setSkill", (str,)),
    "removeAttachment": ("removeAttachment", (int,)),
    "confirm": ("confirm", (str, str)),
    "stop": ("stop", ()),
    "openFolder": ("openFolder", ()),
    "applySettings": ("applySettings", (str, str, str, str, str)),
    "setInterface": ("setInterface", (str, str)),
    "addServer": ("addServer", (str, str, str)),
    "toggleServer": ("toggleServer", (str, bool)),
    "removeServer": ("removeServer", (str,)),
    "checkConnection": ("checkConnection", ()),
    "dismissNotice": ("dismissNotice", ()),
}
MAIN_THREAD_TIMEOUT = 15.0


class BridgeError(Exception):
    def __init__(self, status, message):
        Exception.__init__(self, message)
        self.status = status


def _coerce(values, kinds):
    if not isinstance(values, list) or len(values) != len(kinds):
        raise BridgeError(400, "expected %d arguments" % len(kinds))
    coerced = []
    for value, kind in zip(values, kinds):
        if kind is int and isinstance(value, bool) or not isinstance(value, kind):
            raise BridgeError(400, "argument must be %s" % kind.__name__)
        coerced.append(value)
    return coerced


def inside(root, path):
    root = os.path.realpath(root)
    path = os.path.realpath(path)
    return path == root or path.startswith(root + os.sep)


class WebBridge(object):
    def __init__(self, controller, files_root, upload_dir):
        self._controller = controller
        self._files_root = files_root
        self._upload_dir = upload_dir
        self._condition = threading.Condition()
        self._version = 0
        self._encoded = None

    def publish(self, view):
        encoded = json.dumps(view, ensure_ascii=False, default=str)
        with self._condition:
            if encoded == self._encoded:
                return
            self._encoded = encoded
            self._version += 1
            self._condition.notify_all()

    def snapshot(self, since, timeout):
        with self._condition:
            if self._encoded is None or self._version == since:
                self._condition.wait(timeout)
            return self._version, self._encoded

    def on_main(self, function):
        done = threading.Event()
        outcome = {}

        def run():
            try:
                outcome["value"] = function()
            except Exception as error:
                outcome["error"] = error
            finally:
                done.set()

        self._controller.post(run)
        if not done.wait(MAIN_THREAD_TIMEOUT):
            raise BridgeError(504, "slicer main thread did not respond")
        if "error" in outcome:
            raise BridgeError(500, "%s: %s" % (type(outcome["error"]).__name__, outcome["error"]))
        return outcome.get("value")

    def act(self, name, args):
        if name not in ACTIONS:
            raise BridgeError(404, "unknown action")
        method, kinds = ACTIONS[name]
        values = _coerce(args or [], kinds)
        target = getattr(self._controller, method)
        return self.on_main(lambda: target(*values))

    def open_path(self, path):
        if not isinstance(path, str) or not inside(self._files_root, path):
            raise BridgeError(403, "path is outside the chat folders")
        return self.on_main(lambda: self._controller.openPath(path))

    def readable(self, path):
        if not path or not inside(self._files_root, path) or not os.path.isfile(path):
            raise BridgeError(404, "file not found")
        return os.path.realpath(path)

    def upload(self, name, stream, length):
        name = safe_name(name)
        if not name:
            raise BridgeError(400, "file name is required")
        folder = os.path.join(self._upload_dir, uuid.uuid4().hex[:12])
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, name)
        remaining = length
        with open(path, "wb") as handle:
            while remaining > 0:
                chunk = stream.read(min(remaining, 1024 * 1024))
                if not chunk:
                    raise BridgeError(400, "upload ended early")
                handle.write(chunk)
                remaining -= len(chunk)
        self.on_main(lambda: self._controller.attach(path))
        return path
