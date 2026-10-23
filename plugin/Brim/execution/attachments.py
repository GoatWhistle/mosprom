import os
import re

from ..protocol import constants
from ..protocol.backend_http import BackendHttpError
from .errors import OperationError
from .operations import MODEL_EXTENSIONS

NAME_PATTERN = re.compile(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', re.IGNORECASE)


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
            match = NAME_PATTERN.search(disposition)
            name = match.group(1) if match else None
        name = os.path.basename(name or "")
        if os.path.splitext(name)[1].lower() not in MODEL_EXTENSIONS:
            raise OperationError(constants.ERR_INVALID_ARGUMENTS,
                                 "attachment %s has no supported model extension (stl, obj, 3mf)" % attachment_id)
        directory = os.path.join(self._cache_dir, "attachments", re.sub(r"[^A-Za-z0-9_.-]", "_", attachment_id))
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, name)
        with open(path, "wb") as handle:
            handle.write(payload)
        return path
