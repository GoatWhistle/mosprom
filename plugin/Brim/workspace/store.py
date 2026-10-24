import datetime
import json
import os
import threading
import time
import uuid

INDEX_NAME = "index.json"
CHAT_NAME = "chat.json"
SCENE_NAME = "scene.3mf"
TITLE_LIMIT = 60
REPLACE_ATTEMPTS = 10
REPLACE_PAUSE = 0.1


def _now():
    return datetime.datetime.now().isoformat()


def _title(messages):
    for message in messages:
        if message.get("role") == "user" and not message.get("brim_hidden"):
            text = " ".join(str(message.get("content") or "").split())
            if not text:
                names = [item.get("name", "") for item in message.get("brim_attachments") or []]
                text = ", ".join(name for name in names if name)
            if text:
                return text if len(text) <= TITLE_LIMIT else text[:TITLE_LIMIT - 1] + "…"
    return ""


def _replace(source, target):
    for attempt in range(REPLACE_ATTEMPTS):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == REPLACE_ATTEMPTS - 1:
                raise
            time.sleep(REPLACE_PAUSE)


def _write_json(path, data):
    temporary = path + ".part"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, sort_keys=True)
    _replace(temporary, path)


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


class WorkspaceStore(object):
    def __init__(self, directory):
        self._directory = directory
        self._lock = threading.RLock()
        os.makedirs(directory, exist_ok=True)

    def _index_path(self):
        return os.path.join(self._directory, INDEX_NAME)

    def _read(self):
        data = _read_json(self._index_path())
        if data is not None and isinstance(data.get("items"), dict):
            return data
        return {"active": None, "items": {}}

    def directory(self, conversation_id):
        return os.path.join(self._directory, conversation_id)

    def files_dir(self, conversation_id):
        return os.path.join(self.directory(conversation_id), "files")

    def output_dir(self, conversation_id):
        path = os.path.join(self.directory(conversation_id), "output")
        os.makedirs(path, exist_ok=True)
        return path

    def _chat_path(self, conversation_id):
        return os.path.join(self.directory(conversation_id), CHAT_NAME)

    def create(self, mode, skill=None):
        conversation_id = uuid.uuid4().hex
        now = _now()
        chat = {"id": conversation_id, "title": "", "mode": mode, "skill": skill, "created_at": now, "updated_at": now,
                "messages": []}
        with self._lock:
            os.makedirs(self.directory(conversation_id), exist_ok=True)
            _write_json(self._chat_path(conversation_id), chat)
        return self.row(chat)

    def row(self, chat):
        return {"id": chat["id"], "title": chat.get("title") or "", "mode": chat.get("mode") or "ask",
                "skill": chat.get("skill"), "updated_at": chat.get("updated_at") or ""}

    def chats(self):
        rows = []
        with self._lock:
            for name in os.listdir(self._directory):
                chat = _read_json(os.path.join(self._directory, name, CHAT_NAME))
                if chat is not None and chat.get("id") == name:
                    rows.append(self.row(chat))
        rows.sort(key=lambda item: item["updated_at"], reverse=True)
        return rows

    def load(self, conversation_id):
        with self._lock:
            chat = _read_json(self._chat_path(conversation_id))
        if chat is None:
            raise KeyError(conversation_id)
        chat.setdefault("messages", [])
        return chat

    def _update(self, conversation_id, change):
        with self._lock:
            chat = self.load(conversation_id)
            change(chat)
            chat["updated_at"] = _now()
            _write_json(self._chat_path(conversation_id), chat)
            return chat

    def save_messages(self, conversation_id, messages):
        def change(chat):
            chat["messages"] = messages
            if not chat.get("title"):
                chat["title"] = _title(messages)

        return self.row(self._update(conversation_id, change))

    def set_mode(self, conversation_id, mode):
        return self.row(self._update(conversation_id, lambda chat: chat.__setitem__("mode", mode)))

    def set_skill(self, conversation_id, skill):
        return self.row(self._update(conversation_id, lambda chat: chat.__setitem__("skill", skill)))

    def path_for(self, conversation_id):
        return os.path.join(self.directory(conversation_id), SCENE_NAME)

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
        return dict((key, self.status(key)) for key in self._read()["items"])

    def commit(self, conversation_id):
        with self._lock:
            data = self._read()
            _replace(self.temp_path(conversation_id), self.path_for(conversation_id))
            data["items"][conversation_id] = {"state": "saved", "saved_at": int(time.time())}
            _write_json(self._index_path(), data)

    def mark_empty(self, conversation_id):
        with self._lock:
            data = self._read()
            try:
                os.remove(self.path_for(conversation_id))
            except OSError:
                pass
            data["items"][conversation_id] = {"state": "empty", "saved_at": int(time.time())}
            _write_json(self._index_path(), data)

    def discard_temp(self, conversation_id):
        try:
            os.remove(self.temp_path(conversation_id))
        except OSError:
            pass

    def active(self):
        active = self._read()["active"]
        if active is not None and not os.path.isfile(self._chat_path(active)):
            return None
        return active

    def set_active(self, conversation_id):
        with self._lock:
            data = self._read()
            data["active"] = conversation_id
            _write_json(self._index_path(), data)
