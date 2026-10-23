import io
import os
import threading

from ..execution.errors import OperationError
from ..protocol import constants

SLICE_TIMEOUT = 900.0


class SlicingService(object):
    def __init__(self, host, main, state):
        self._h = host
        self._main = main
        self._state = state
        self._cancel = threading.Event()

    def cancel(self):
        self._cancel.set()
        self._main.call(self._stop)

    def _stop(self):
        backend = self._h.backend()
        if hasattr(backend, "stopSlicing"):
            backend.stopSlicing()

    def begin_batch(self):
        self._main.call(self._set_timer, False)

    def end_batch(self):
        self._main.call(self._set_timer, True)

    def _set_timer(self, restore):
        backend = self._h.backend()
        if restore:
            if hasattr(backend, "determineAutoSlicing"):
                backend.determineAutoSlicing()
        elif hasattr(backend, "disableTimer"):
            backend.disableTimer()

    def slice(self, report):
        self._cancel.clear()
        done = threading.Event()
        result = {}
        done_state = self._h.BackendState.Done
        error_state = self._h.BackendState.Error

        def on_state(state):
            self._state.slice_state = {2: "processing", 3: "done", 4: "error", 5: "disabled"}.get(int(state), "not_started")
            if state == done_state or state == error_state:
                result["state"] = state
                done.set()

        def on_progress(fraction):
            report("slicing", float(fraction))

        backend = self._main.call(self._h.backend)
        self._main.call(backend.backendStateChange.connect, on_state)
        self._main.call(backend.processingProgress.connect, on_progress)
        try:
            self._main.call(backend.forceSlice)
            finished = False
            elapsed = 0.0
            while not finished and elapsed < SLICE_TIMEOUT and not self._cancel.is_set():
                finished = done.wait(1.0)
                elapsed += 1.0
        finally:
            self._main.call(backend.backendStateChange.disconnect, on_state)
            self._main.call(backend.processingProgress.disconnect, on_progress)
        if self._cancel.is_set():
            raise OperationError(constants.ERR_CANCELLED, "slicing was cancelled")
        if not finished:
            raise OperationError(constants.ERR_SLICE_FAILED, "slicing did not finish within %.0f s" % SLICE_TIMEOUT)
        if result["state"] == error_state:
            raise OperationError(constants.ERR_SLICE_FAILED, "the slicer engine reported an error",
                                 {"slicer_errors": list(self._state.errors)})
        return self._main.call(self._summary)

    def _summary(self):
        info = self._h.application.getPrintInformation()
        if info is None:
            return {}
        duration = info.currentPrintTime
        return {
            "print_time_seconds": int(duration.days * 86400 + duration.hours * 3600 + duration.minutes * 60),
            "material_weight_g": [round(float(item), 2) for item in info.materialWeights],
            "material_length_m": [round(float(item), 2) for item in info.materialLengths],
        }

    def export(self, directory):
        gcode_path = os.path.join(directory, "result.gcode")
        project_path = os.path.join(directory, "result.3mf")
        self._main.call(self._write_gcode, gcode_path)
        self._main.call(self._write_project, project_path)
        return {"gcode": gcode_path, "3mf": project_path}

    def _write_gcode(self, path):
        writer = self._h.plugin("GCodeWriter")
        stream = io.StringIO()
        if writer is None or not writer.write(stream, None):
            raise OperationError(constants.ERR_OPERATION_FAILED, "G-code writer failed",
                                 {"writer_error": str(getattr(writer, "getInformation", lambda: "")())})
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(stream.getvalue())

    def _write_project(self, path):
        writer = self._h.application.getWorkspaceFileHandler().getWriter("3MFWriter")
        stream = io.BytesIO()
        if writer is None or not writer.write(stream, None):
            raise OperationError(constants.ERR_OPERATION_FAILED, "3MF project writer failed")
        with open(path, "wb") as handle:
            handle.write(stream.getvalue())
