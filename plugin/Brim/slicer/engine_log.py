import os
import re

FATAL = re.compile(r"Failed to intersect model|No SCAD available|differece model|setting with no value given")
ERROR = re.compile(r" - (ERROR|CRITICAL) - |\[ERROR\]")
IGNORED = re.compile(r"MachineErrorChecker|QmlWarning|PostProcessingPlugin|No module named 'statistics'|"
                     r"Connection reset by peer")
MAX_LINES = 12
MAX_LINE = 300


class EngineLog(object):
    def __init__(self, path):
        self._path = path
        self._offset = 0

    def mark(self):
        try:
            self._offset = os.path.getsize(self._path) if self._path else 0
        except OSError:
            self._offset = 0

    def _new_lines(self):
        if not self._path:
            return []
        try:
            with open(self._path, "rb") as handle:
                handle.seek(self._offset)
                data = handle.read()
        except (IOError, OSError):
            return []
        return [line.strip() for line in data.decode("utf-8", "replace").splitlines()]

    def errors(self):
        found = [line for line in self._new_lines() if ERROR.search(line) and not IGNORED.search(line)]
        return [line[:MAX_LINE] for line in found[-MAX_LINES:]]

    def fatal(self):
        return any(FATAL.search(line) and not IGNORED.search(line) for line in self._new_lines())
