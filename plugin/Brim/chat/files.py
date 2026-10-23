import os

from ..execution.operations import MODEL_EXTENSIONS

ATTACHMENT_EXTENSIONS = (".jpg", ".jpeg", ".png") + MODEL_EXTENSIONS
MAX_ATTACHMENT_BYTES = 100 * 1024 * 1024
MAX_ATTACHMENTS = 8


class ChatFiles(object):
    def __init__(self, state, http, submit, notice, strings):
        self._state = state
        self._http = http
        self._submit = submit
        self._notice = notice
        self._strings = strings

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

        def work():
            with open(path, "rb") as handle:
                return self._http.upload_attachment(name, handle.read())

        def done(meta):
            self._state.attachments.append({"id": meta["id"], "name": meta.get("name", name), "size": meta.get("size", size)})

        self._submit(work, done, busy=True)

    def save(self, kind, destination):
        run_id = (self._state.result or {}).get("run_id") or self._state.run_id
        if run_id is None:
            return

        def work():
            payload, _ = self._http.download_artifact(run_id, kind)
            with open(destination, "wb") as handle:
                handle.write(payload)
            return destination

        def done(path):
            self._notice("%s: %s" % (self._strings()["saved"], path))

        self._submit(work, done, busy=True)
