import hashlib
import json
import os

from ..protocol import constants
from ..protocol.backend_http import BackendHttpError
from .errors import OperationError

CHUNK_SIZE = 1024 * 1024
KINDS = ("gcode", "3mf")


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


class ArtifactSet(object):
    def __init__(self, scene_version, files, hashes):
        self.scene_version = scene_version
        self.files = files
        self.hashes = hashes
        self.uploaded = set()

    def pending_kinds(self):
        return [kind for kind in KINDS if kind not in self.uploaded]

    def describe(self):
        return dict((kind, {"sha256": self.hashes[kind], "size": os.path.getsize(self.files[kind]),
                            "uploaded": kind in self.uploaded}) for kind in KINDS)


class ArtifactService(object):
    def __init__(self, http_client, cache_dir):
        self._http = http_client
        self._cache_dir = cache_dir
        self._current = None

    def directory(self):
        os.makedirs(self._cache_dir, exist_ok=True)
        return self._cache_dir

    def register(self, scene_version, files):
        hashes = dict((kind, file_sha256(files[kind])) for kind in KINDS)
        self._current = ArtifactSet(scene_version, files, hashes)
        with open(os.path.join(self.directory(), "manifest.json"), "w", encoding="utf-8") as handle:
            json.dump({"scene_version": scene_version, "files": files, "sha256": hashes}, handle)
        return self._current

    def reusable(self, scene_version):
        current = self._current
        if current is not None and current.scene_version == scene_version and current.pending_kinds():
            return current
        return None

    def upload(self, run_id, artifact_set, report=None):
        pending = artifact_set.pending_kinds()
        for position, kind in enumerate(pending):
            self._upload_kind(run_id, artifact_set, kind)
            if report:
                report("upload", (position + 1) / float(len(pending)))
        return artifact_set.describe()

    def _upload_kind(self, run_id, artifact_set, kind):
        path = artifact_set.files[kind]
        size = os.path.getsize(path)
        count = max(1, (size + CHUNK_SIZE - 1) // CHUNK_SIZE)
        receipt = None
        try:
            with open(path, "rb") as handle:
                for index in range(count):
                    receipt = self._http.upload_artifact_chunk(run_id, kind, artifact_set.scene_version, index, count,
                                                               artifact_set.hashes[kind], handle.read(CHUNK_SIZE))
        except BackendHttpError as error:
            raise OperationError(constants.ERR_UPLOAD_FAILED, "upload of %s failed: %s" % (kind, error),
                                 {"kind": kind, "retry": "send slice again to resend without reslicing"})
        stored = (receipt or {}).get("artifact") or {}
        if not (receipt or {}).get("complete") or stored.get("sha256") != artifact_set.hashes[kind] \
                or stored.get("size") != size:
            raise OperationError(constants.ERR_UPLOAD_FAILED, "backend did not confirm storing %s" % kind,
                                 {"kind": kind, "receipt": receipt, "retry": "send slice again to resend without reslicing"})
        artifact_set.uploaded.add(kind)
