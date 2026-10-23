from ..execution.errors import OperationError
from ..protocol import constants

SUPPORTED_VIEWS = ("iso",)


class Renderer(object):
    def __init__(self, host, main, http_client):
        self._h = host
        self._main = main
        self._http = http_client

    def render(self, view):
        if view not in SUPPORTED_VIEWS:
            raise OperationError(constants.ERR_NOT_AVAILABLE, "view %s is not supported" % view,
                                 {"supported_views": list(SUPPORTED_VIEWS)})
        data = self._main.call(self._snapshot)
        if not data:
            raise OperationError(constants.ERR_OPERATION_FAILED, "the scene is empty, nothing to render")
        meta = self._http.upload_attachment("scene-%s.png" % view, data)
        return {"attachment_id": meta["id"], "view": view, "width": 800, "height": 800}

    def _snapshot(self):
        image = self._h.Snapshot.snapshot(width=800, height=800)
        if image is None:
            return None
        buffer = self._h.QBuffer()
        buffer.open(self._h.QIODevice.WriteOnly)
        image.save(buffer, "PNG")
        return bytes(buffer.data())
