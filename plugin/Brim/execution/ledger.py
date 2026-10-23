import json
import os
import threading

from ..protocol import constants, frames

RUNNING = "running"
DONE = "done"
DELIVERED = "delivered"
MAX_ENTRIES = 500


class CallLedger(object):
    def __init__(self, path=None):
        self._path = path
        self._lock = threading.Lock()
        self._entries = {}
        self._order = []
        self._load()

    def _load(self):
        if not self._path or not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            return
        for item in data.get("entries", []):
            entry = item["entry"]
            if entry["state"] == RUNNING:
                entry = self._unknown(item["call_id"], entry)
            self._entries[item["call_id"]] = entry
            self._order.append(item["call_id"])

    def _unknown(self, call_id, entry):
        error = frames.error_object(constants.ERR_OUTCOME_UNKNOWN, "plugin restarted while the call was running")
        frame = frames.tool_result_frame(call_id, entry.get("run_id"), False, entry.get("scene_version"), {}, error, [])
        return {"state": DONE, "run_id": entry.get("run_id"), "scene_version": entry.get("scene_version"), "frame": frame,
                "fingerprint": entry.get("fingerprint")}

    def _save(self):
        if not self._path:
            return
        data = {"entries": [{"call_id": call_id, "entry": self._entries[call_id]} for call_id in self._order]}
        temporary = self._path + ".tmp"
        try:
            with open(temporary, "w", encoding="utf-8") as handle:
                json.dump(data, handle)
            os.replace(temporary, self._path)
        except OSError:
            pass

    def begin(self, call_id, run_id, scene_version, fingerprint=None):
        with self._lock:
            if call_id in self._entries:
                return False
            self._entries[call_id] = {"state": RUNNING, "run_id": run_id, "scene_version": scene_version, "frame": None,
                                      "fingerprint": fingerprint}
            self._order.append(call_id)
            while len(self._order) > MAX_ENTRIES:
                self._entries.pop(self._order.pop(0), None)
            self._save()
            return True

    def finish(self, call_id, frame):
        with self._lock:
            entry = self._entries.get(call_id)
            if entry is None:
                return
            entry["state"] = DONE
            entry["frame"] = frame
            self._save()

    def mark_delivered(self, call_id):
        with self._lock:
            entry = self._entries.get(call_id)
            if entry is not None and entry["state"] == DONE:
                entry["state"] = DELIVERED
                self._save()

    def fingerprint(self, call_id):
        with self._lock:
            entry = self._entries.get(call_id)
            return entry.get("fingerprint") if entry else None

    def state(self, call_id):
        with self._lock:
            entry = self._entries.get(call_id)
            return entry["state"] if entry else None

    def result_frame(self, call_id):
        with self._lock:
            entry = self._entries.get(call_id)
            if entry is None or entry["state"] == RUNNING:
                return None
            return entry["frame"]

    def running_ids(self):
        with self._lock:
            return [call_id for call_id, entry in self._entries.items() if entry["state"] == RUNNING]

    def undelivered_ids(self):
        with self._lock:
            return [call_id for call_id, entry in self._entries.items() if entry["state"] == DONE]
