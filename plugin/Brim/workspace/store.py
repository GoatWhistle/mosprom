import json
import os
import time

INDEX_NAME = "index.json"


class WorkspaceStore(object):
    def __init__(self, directory):
        self._directory = directory
        os.makedirs(directory, exist_ok=True)

    def _index_path(self):
        return os.path.join(self._directory, INDEX_NAME)

    def _read(self):
        try:
            with open(self._index_path(), "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict) and isinstance(data.get("items"), dict):
                return data
        except (OSError, ValueError):
            pass
        return {"active": None, "items": {}}

    def _write(self, data):
        target = self._index_path()
        temporary = target + ".part"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(data, handle, sort_keys=True)
        os.replace(temporary, target)

    def path_for(self, conversation_id):
        return os.path.join(self._directory, "%s.3mf" % conversation_id)

    def temp_path(self, conversation_id):
        return self.path_for(conversation_id) + ".part"

    def status(self, conversation_id):
        item = self._read()["items"].get(conversation_id)
        if item is None:
            return "none"
        if item["state"] == "saved" and not os.path.isfile(self.path_for(conversation_id)):
            return "none"
        return item["state"]

    def statuses(self):
        return {key: self.status(key) for key in self._read()["items"]}

    def commit(self, conversation_id):
        data = self._read()
        os.replace(self.temp_path(conversation_id), self.path_for(conversation_id))
        data["items"][conversation_id] = {"state": "saved", "saved_at": int(time.time())}
        self._write(data)

    def mark_empty(self, conversation_id):
        data = self._read()
        try:
            os.remove(self.path_for(conversation_id))
        except OSError:
            pass
        data["items"][conversation_id] = {"state": "empty", "saved_at": int(time.time())}
        self._write(data)

    def discard_temp(self, conversation_id):
        try:
            os.remove(self.temp_path(conversation_id))
        except OSError:
            pass

    def active(self):
        return self._read()["active"]

    def set_active(self, conversation_id):
        data = self._read()
        data["active"] = conversation_id
        self._write(data)
