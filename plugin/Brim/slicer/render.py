from ..execution.errors import OperationError
from ..protocol import constants

SUPPORTED_VIEWS = ("iso",)
SIZE = 800


class Renderer(object):
    def __init__(self, host, main):
        self._h = host
        self._main = main

    def render(self, view):
        if view not in SUPPORTED_VIEWS:
            raise OperationError(constants.ERR_NOT_AVAILABLE, "view %s is not supported" % view,
                                 {"supported_views": list(SUPPORTED_VIEWS)})
        data = self._main.call(self._snapshot)
        if not data:
            raise OperationError(constants.ERR_OPERATION_FAILED, "the scene is empty, nothing to render")
        return {"view": view, "width": SIZE, "height": SIZE, "png": data}

    def _snapshot(self):
        image = self._h.Snapshot.snapshot(width=SIZE, height=SIZE)
        if image is None:
            return None
        buffer = self._h.QBuffer()
        buffer.open(self._h.QIODevice.WriteOnly)
        image.save(buffer, "PNG")
        return bytes(buffer.data())
