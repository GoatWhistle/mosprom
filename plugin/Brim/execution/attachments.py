import os
import re
from urllib.parse import unquote

from ..protocol import constants
from ..protocol.backend_http import BackendHttpError
from .errors import OperationError
from .operations import MODEL_EXTENSIONS

ENCODED_NAME = re.compile(r"filename\*\s*=\s*UTF-8''([^;\s]+)", re.IGNORECASE)
PLAIN_NAME = re.compile(r'filename\s*=\s*"?([^";]+)"?', re.IGNORECASE)
UNSAFE_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def disposition_name(value):
    match = ENCODED_NAME.search(value)
    if match:
        return unquote(match.group(1), encoding="utf-8", errors="replace")
    match = PLAIN_NAME.search(value)
    return match.group(1) if match else None


def safe_name(name):
    return UNSAFE_NAME_CHARS.sub("_", os.path.basename(name or "").replace("\\", "/").split("/")[-1])


class AttachmentCache(object):
    def __init__(self, http_client, cache_dir):
        self._http = http_client
        self._cache_dir = cache_dir

    def fetch(self, attachment_id, name_hint=None):
        try:
            payload, headers = self._http.download_attachment(attachment_id)
        except BackendHttpError as error:
            raise OperationError(constants.ERR_OPERATION_FAILED, "attachment %s unavailable: %s" % (attachment_id, error))
        name = name_hint
        disposition = headers.get("Content-Disposition") if hasattr(headers, "get") else None
        if not name and disposition:
            name = disposition_name(disposition)
        name = safe_name(name)
        if os.path.splitext(name)[1].lower() not in MODEL_EXTENSIONS:
            raise OperationError(constants.ERR_INVALID_ARGUMENTS,
                                 "attachment %s has no supported model extension (stl, obj, 3mf)" % attachment_id)
        directory = os.path.join(self._cache_dir, "attachments", re.sub(r"[^A-Za-z0-9_.-]", "_", attachment_id))
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, name)
        with open(path, "wb") as handle:
            handle.write(payload)
        return path
