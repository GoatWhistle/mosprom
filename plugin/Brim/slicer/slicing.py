import io
import os
import threading
import time

from ..execution.errors import OperationError
from ..protocol import constants
from .engine_log import EngineLog
from .project_archive import verify_project
from .qt_wrappers import direct_qt_calls

SLICE_TIMEOUT = 2700.0
FATAL_GRACE = 20.0
ERROR_CHECK_TIMEOUT = 180.0
ERROR_CHECK_PAUSE = 0.5
ESTIMATE_RETRIES = 10
ESTIMATE_PAUSE = 0.5


def _by_extruder(values, positions):
    values = [round(float(item), 2) for item in values]
    if not positions or len(positions) != len(values) or sorted(positions) != list(range(len(values))):
        return values
    ordered = [0.0] * len(values)
    for position, value in zip(positions, values):
        ordered[position] = value
    return ordered


class SlicingService(object):
    def __init__(self, host, main, state):
        self._h = host
        self._main = main
        self._state = state
        self._cancel = threading.Event()
        log_path = getattr(host, "log_path", None)
        self._log = EngineLog(log_path() if callable(log_path) else None)

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

    def slice(self, report, check=None):
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

        self._wait_error_check()
        backend = self._main.call(self._h.backend)
        self._log.mark()
        self._main.call(backend.backendStateChange.connect, on_state)
        self._main.call(backend.processingProgress.connect, on_progress)
        try:
            self._main.call(backend.forceSlice, guard=check)
            finished = False
            elapsed = 0.0
            fatal_at = None
            while not finished and elapsed < SLICE_TIMEOUT and not self._cancel.is_set():
                finished = done.wait(1.0)
                elapsed += 1.0
                if fatal_at is None and int(elapsed) % 5 == 0 and self._log.fatal():
                    fatal_at = elapsed
                if fatal_at is not None and elapsed - fatal_at >= FATAL_GRACE:
                    break
        finally:
            self._main.call(backend.backendStateChange.disconnect, on_state)
            self._main.call(backend.processingProgress.disconnect, on_progress)
        if self._cancel.is_set():
            raise OperationError(constants.ERR_CANCELLED, "slicing was cancelled")
        if not finished:
            self._main.call(self._stop)
            raise OperationError(constants.ERR_SLICE_FAILED, "slicing stopped without a result after %.0f s" % elapsed,
                                 {"engine_log": self._log.errors()})
        if result["state"] == error_state:
            raise OperationError(constants.ERR_SLICE_FAILED, "the slicer engine reported an error",
                                 {"slicer_errors": list(self._state.errors), "engine_log": self._log.errors()})
        summary = self._main.call(self._summary)
        for _ in range(ESTIMATE_RETRIES):
            if summary.get("print_time_seconds") is not None:
                break
            time.sleep(ESTIMATE_PAUSE)
            summary = self._main.call(self._summary)
        return summary

    def _wait_error_check(self):
        waited = 0.0
        while waited < ERROR_CHECK_TIMEOUT and not self._cancel.is_set():
            if not self._main.call(self._error_check_pending):
                return
            time.sleep(ERROR_CHECK_PAUSE)
            waited += ERROR_CHECK_PAUSE

    def _error_check_pending(self):
        getter = getattr(self._h.application, "getMachineErrorChecker", None)
        checker = getter() if callable(getter) else None
        return bool(getattr(checker, "needToWaitForResult", False))

    def _summary(self):
        info = self._h.application.getPrintInformation()
        if info is None:
            return {}
        duration = info.currentPrintTime
        seconds = None
        if duration is not None and duration.valid:
            seconds = int(duration.days * 86400 + duration.hours * 3600 + duration.minutes * 60 + duration.seconds)
        positions = self._estimate_positions(info)
        return {
            "print_time_seconds": seconds,
            "material_weight_g": _by_extruder(info.materialWeights, positions),
            "material_length_m": _by_extruder(info.materialLengths, positions),
        }

    def _estimate_positions(self, info):
        stack = self._h.global_stack()
        if stack is None:
            return None
        amounts = getattr(info, "_material_amounts", None)
        positions = [int(key) for key in stack.extruders]
        if amounts is not None:
            positions = [item for item in positions if item < len(amounts)]
        return positions

    def export(self, directory, check=None):
        gcode_path = os.path.join(directory, "result.gcode")
        project_path = os.path.join(directory, "result.3mf")
        self._main.call(self._write_gcode, gcode_path, guard=check)
        self._main.call(self._write_project, project_path, guard=check)
        verify_project(project_path)
        return {"gcode": gcode_path, "3mf": project_path}

    def write_project(self, path):
        self._main.call(self._write_project, path)

    def _write_gcode(self, path):
        writer = self._h.plugin("GCodeWriter")
        stream = io.StringIO()
        if writer is None or not self._write_on_qt_thread(writer, stream, None, "_createSnapshot"):
            raise OperationError(constants.ERR_OPERATION_FAILED, "G-code writer failed",
                                 {"writer_error": str(getattr(writer, "getInformation", lambda: "")())})
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(stream.getvalue())

    def _write_project(self, path):
        writer = self._h.application.getWorkspaceFileHandler().getWriter("3MFWriter")
        stream = io.BytesIO()
        nodes = [self._h.scene().getRoot()]
        if writer is None or not self._write_on_qt_thread(writer, stream, nodes, "write"):
            raise OperationError(constants.ERR_OPERATION_FAILED, "3MF project writer failed")
        with open(path, "wb") as handle:
            handle.write(stream.getvalue())

    def _write_on_qt_thread(self, writer, stream, nodes, *wrapped):
        with direct_qt_calls(writer, *wrapped):
            return writer.write(stream, nodes)
