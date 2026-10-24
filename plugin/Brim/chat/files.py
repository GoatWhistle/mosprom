import os
import re
import shutil
import uuid

from ..documents.reader import DOCUMENT_TYPES, MAX_DOCUMENT_BYTES
from ..execution.operations import MODEL_EXTENSIONS

IMAGE_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
ATTACHMENT_EXTENSIONS = tuple(IMAGE_TYPES) + MODEL_EXTENSIONS + tuple(DOCUMENT_TYPES)
MAX_ATTACHMENT_BYTES = 100 * 1024 * 1024
MAX_ATTACHMENTS = 8
UNSAFE_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_name(name):
    return UNSAFE_NAME_CHARS.sub("_", os.path.basename(name or "").replace("\\", "/").split("/")[-1])


def describe(path):
    name = os.path.basename(path)
    extension = os.path.splitext(name)[1].lower()
    if extension in IMAGE_TYPES:
        return {"name": name, "path": path, "kind": "image", "mime_type": IMAGE_TYPES[extension]}
    if extension in DOCUMENT_TYPES:
        return {"name": name, "path": path, "kind": "document", "mime_type": DOCUMENT_TYPES[extension]}
    return {"name": name, "path": path, "kind": "model", "mime_type": "application/octet-stream"}


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
            self._notice("%s: %s" % (name, ", ".join(item[1:].upper() for item in ATTACHMENT_EXTENSIONS)))
            return
        if len(self._state.attachments) >= MAX_ATTACHMENTS:
            self._notice("max %d" % MAX_ATTACHMENTS)
            return
        try:
            size = os.path.getsize(path)
        except OSError as error:
            self._notice(str(error))
            return
        item = describe(path)
        limit = MAX_DOCUMENT_BYTES if item["kind"] == "document" else MAX_ATTACHMENT_BYTES
        if size > limit:
            self._notice("%s: %d MiB > %d MiB" % (name, size // (1024 * 1024), limit // (1024 * 1024)))
            return
        self._state.attachments.append(dict(item, size=size))
        self._notice(self._state.notice)
