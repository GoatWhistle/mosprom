import copy
import os
import threading
import uuid

IMAGE_EXTENSIONS = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/webp": ".webp"}


class Conversation(object):
    def __init__(self, conversation_id, messages, persist, files_dir):
        self.id = conversation_id
        self._messages = list(messages)
        self._persist = persist
        self.files_dir = files_dir
        self._lock = threading.Lock()

    def messages(self):
        with self._lock:
            return copy.deepcopy(self._messages)

    def append(self, message):
        with self._lock:
            self._messages.append(message)
            return len(self._messages) - 1

    def update(self, index, message):
        with self._lock:
            self._messages[index] = message

    def save(self):
        with self._lock:
            snapshot = copy.deepcopy(self._messages)
        self._persist(snapshot)

    def save_image(self, data, mime_type):
        os.makedirs(self.files_dir, exist_ok=True)
        path = os.path.join(self.files_dir, "image-%s%s" % (uuid.uuid4().hex[:12], IMAGE_EXTENSIONS.get(mime_type, ".png")))
        with open(path, "wb") as handle:
            handle.write(data)
        return {"path": path, "mime_type": mime_type}


def read_file(path):
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except (IOError, OSError):
        return None
