import json
import threading

from ..protocol import constants, frames
from . import geometry
from .errors import OperationError, OutcomeUnknown
from .operations import validate_operations


class ToolExecutor(object):
    def __init__(self, port, ledger, attachments, artifacts):
        self._port = port
        self._ledger = ledger
        self._attachments = attachments
        self._artifacts = artifacts
        self._cancelled = set()
        self._lock = threading.Lock()
        self._tools = {
            constants.TOOL_APPLY_CHANGES: self._apply_changes,
            constants.TOOL_SEARCH_SETTINGS: self._search_settings,
            constants.TOOL_INSPECT_PROFILE: self._inspect_profile,
            constants.TOOL_INSPECT_MATERIAL: self._inspect_material,
            constants.TOOL_ANALYZE_GEOMETRY: self._analyze_geometry,
            constants.TOOL_RENDER_SCENE: self._render_scene,
            constants.TOOL_SLICE: self._slice,
        }

    def cancel_run(self, run_id):
        with self._lock:
            self._cancelled.add(run_id)
        self._port.cancel_slice()

    def _is_cancelled(self, run_id):
        with self._lock:
            return run_id in self._cancelled

    def execute_call(self, call, report=None):
        call_id = call.get("call_id")
        run_id = call.get("run_id")
        fingerprint = self._fingerprint(call.get("tool"), call.get("arguments"))
        known = self._ledger.fingerprint(call_id)
        if known is not None and known != fingerprint:
            return self._failure_frame(call_id, run_id, constants.ERR_CALL_CONFLICT,
                                       "call_id was already used with different content")
        stored = self._ledger.result_frame(call_id)
        if stored is not None:
            return stored
        if self._ledger.state(call_id) is not None:
            return self._failure_frame(call_id, run_id, constants.ERR_IN_PROGRESS, "call is still running")
        expected = call.get("expected_scene_version")
        current = self._port.scene_version()
        if expected is not None and expected != current:
            error = frames.error_object(constants.ERR_STALE_SCENE, "scene changed: expected %s, actual %s" % (expected, current))
            return frames.tool_result_frame(call_id, run_id, False, current, {"state": self._port.read_state()}, error, [])
        if not self._ledger.begin(call_id, run_id, current, fingerprint):
            return self._ledger.result_frame(call_id) or self._failure_frame(
                call_id, run_id, constants.ERR_IN_PROGRESS, "call is still running")
        outcome = self._run(call.get("tool"), call.get("arguments") or {}, call_id, run_id, report)
        frame = frames.tool_result_frame(call_id, run_id, outcome["ok"], outcome["scene_version"],
                                         outcome.get("result"), outcome.get("error"), outcome.get("applied"))
        self._ledger.finish(call_id, frame)
        return frame

    def execute_mcp(self, name, arguments, request_id):
        call_id = "mcp-%s" % frames.new_id()
        self._ledger.begin(call_id, None, self._port.scene_version())
        outcome = self._run(name, arguments, call_id, None, None)
        self._ledger.finish(call_id, frames.tool_result_frame(call_id, None, outcome["ok"], outcome["scene_version"],
                                                              outcome.get("result"), outcome.get("error"), outcome.get("applied")))
        return outcome

    def _fingerprint(self, tool, arguments):
        return json.dumps([tool, arguments or {}], sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def _failure_frame(self, call_id, run_id, code, message):
        return frames.tool_result_frame(call_id, run_id, False, self._port.scene_version(), {},
                                        frames.error_object(code, message), [])

    def _run(self, tool, arguments, call_id, run_id, report):
        handler = self._tools.get(tool)
        applied = []
        try:
            if handler is None:
                raise OperationError(constants.ERR_UNKNOWN_TOOL, "tool %s is not executed by the plugin" % tool)
            result = handler(arguments, call_id, run_id, report, applied)
            return {"ok": True, "result": result, "error": None, "applied": applied,
                    "scene_version": self._port.scene_version()}
        except OperationError as error:
            result = dict(error.details)
            return {"ok": False, "result": result, "error": frames.error_object(error.code, error.message),
                    "applied": applied, "scene_version": self._port.scene_version()}
        except Exception as error:
            return {"ok": False, "result": {}, "applied": applied, "scene_version": self._port.scene_version(),
                    "error": frames.error_object(constants.ERR_OUTCOME_UNKNOWN, "unexpected failure: %s" % error)}

    def _apply_changes(self, arguments, call_id, run_id, report, applied):
        operations = arguments.get("operations")
        problems = validate_operations(operations)
        if problems:
            raise OperationError(constants.ERR_INVALID_ARGUMENTS, "invalid operations", {"problems": problems})
        self._port.begin_batch()
        try:
            for index, op in enumerate(operations):
                if self._is_cancelled(run_id):
                    raise OperationError(constants.ERR_CANCELLED, "run cancelled", {"stopped_at": index})
                result = self._apply_operation(op)
                applied.append({"index": index, "kind": op["kind"], "result": result})
                if report:
                    report("apply_changes", (index + 1) / float(len(operations)))
        except OperationError as error:
            error.details = dict(error.details, failed_index=len(applied), failed_kind=operations[len(applied)]["kind"],
                                 state=self._port.read_state())
            raise
        except Exception as error:
            raise OutcomeUnknown("operation %d (%s) ended unexpectedly: %s" % (
                len(applied), operations[len(applied)]["kind"], error),
                {"failed_index": len(applied), "state": self._port.read_state()})
        finally:
            self._port.end_batch()
        return {"state": self._port.read_state()}

    def _apply_operation(self, op):
        if op["kind"] in ("import_model", "open_3mf") and not op.get("path"):
            op = dict(op, path=self._attachments.fetch(op["attachment_id"], op.get("name")))
        return self._port.apply_operation(op)

    def _search_settings(self, arguments, call_id, run_id, report, applied):
        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            raise OperationError(constants.ERR_INVALID_ARGUMENTS, "query required")
        return {"matches": self._port.search_settings(query.strip())}

    def _inspect_profile(self, arguments, call_id, run_id, report, applied):
        return self._port.inspect_profile()

    def _inspect_material(self, arguments, call_id, run_id, report, applied):
        return self._port.inspect_material(arguments.get("material_id"))

    def _render_scene(self, arguments, call_id, run_id, report, applied):
        return self._port.render_scene(arguments.get("view") or "iso")

    def _analyze_geometry(self, arguments, call_id, run_id, report, applied):
        ids = arguments.get("object_ids")
        if not isinstance(ids, list) or not ids:
            raise OperationError(constants.ERR_INVALID_ARGUMENTS, "object_ids must be a non-empty list")
        direction = arguments.get("direction")
        if direction is not None and not (isinstance(direction, list) and len(direction) == 3):
            raise OperationError(constants.ERR_INVALID_ARGUMENTS, "direction must be [x, y, z]")
        results = {}
        for object_id in ids:
            mesh = self._port.mesh_snapshot(object_id)
            if mesh is None:
                raise OperationError(constants.ERR_OPERATION_FAILED, "unknown object %s" % object_id)
            try:
                results[object_id] = geometry.analyze(mesh, direction)
            except ValueError as error:
                raise OperationError(constants.ERR_INVALID_ARGUMENTS, str(error))
        return {"objects": results}

    def _slice(self, arguments, call_id, run_id, report, applied):
        version = self._port.scene_version()
        artifact_set = self._artifacts.reusable(version)
        summary = None
        if artifact_set is None:
            summary = self._port.slice(report or (lambda stage, fraction: None))
            if self._port.scene_version() != version:
                raise OperationError(constants.ERR_STALE_RESULT, "scene changed during slicing; result discarded")
            files = self._port.export_artifacts(self._artifacts.directory())
            if self._port.scene_version() != version:
                raise OperationError(constants.ERR_STALE_RESULT, "scene changed during export; result discarded")
            artifact_set = self._artifacts.register(version, files)
        uploaded = self._artifacts.upload(run_id, artifact_set, report)
        return {"slice": summary, "artifacts": uploaded, "scene_version": version}
