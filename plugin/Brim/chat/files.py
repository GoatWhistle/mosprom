import os
import re
import shutil
import uuid

from ..execution.operations import MODEL_EXTENSIONS

IMAGE_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
ATTACHMENT_EXTENSIONS = tuple(IMAGE_TYPES) + MODEL_EXTENSIONS
MAX_ATTACHMENT_BYTES = 100 * 1024 * 1024
MAX_ATTACHMENTS = 8
UNSAFE_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_name(name):
    return UNSAFE_NAME_CHARS.sub("_", os.path.basename(name or "").replace("\\", "/").split("/")[-1])


def describe(path):
    name = os.path.basename(path)
    extension = os.path.splitext(name)[1].lower()
    kind = "image" if extension in IMAGE_TYPES else "model"
    return {"name": name, "path": path, "kind": kind, "mime_type": IMAGE_TYPES.get(extension, "application/octet-stream")}


def copy_into(attachments, directory):
    os.makedirs(directory, exist_ok=True)
    copied = []
    for item in attachments:
        target = os.path.join(directory, "%s-%s" % (uuid.uuid4().hex[:8], safe_name(item["name"])))
        shutil.copyfile(item["path"], target)
        copied.append(dict(item, path=target))
    return copied


class ChatFiles(object):
    def __init__(self, state, notice):
        self._state = state
        self._notice = notice

    def attach(self, path):
        path = str(path)
        name = os.path.basename(path)
        if os.path.splitext(name)[1].lower() not in ATTACHMENT_EXTENSIONS:
            self._notice("%s: JPG, PNG, STL, OBJ, 3MF" % name)
            return
        if len(self._state.attachments) >= MAX_ATTACHMENTS:
            self._notice("max %d" % MAX_ATTACHMENTS)
            return
        try:
            size = os.path.getsize(path)
        except OSError as error:
            self._notice(str(error))
            return
        if size > MAX_ATTACHMENT_BYTES:
            self._notice("%s: %d MiB" % (name, size // (1024 * 1024)))
            return
        self._state.attachments.append(dict(describe(path), size=size))
        self._notice(self._state.notice)
