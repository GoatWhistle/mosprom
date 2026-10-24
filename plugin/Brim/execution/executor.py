import json
import os
import threading

from ..calibration.journal import run_journal
from ..calibration.models import generate
from ..documents.reader import read_document
from ..engineering.calculations import calculate
from ..protocol import constants
from . import geometry
from .errors import OperationError, OutcomeUnknown
from .operations import validate_operations


def error_object(code, message):
    return {"code": code, "message": message}


def state_summary(state):
    printer = state.get("printer") or {}
    return {"mode": state.get("mode"), "profile": state.get("profile"), "overrides": state.get("overrides"),
            "materials": [{"extruder": item.get("index"), "material_id": item.get("material_id")}
                          for item in printer.get("extruders") or []],
            "objects": [{"id": item.get("id"), "name": item.get("name")} for item in state.get("objects") or []]}


class ToolExecutor(object):
    def __init__(self, port, output_dir, files_dir=None, skills=None, defects=None, materials=None):
        self._port = port
        self._output_dir = output_dir
        self._files_dir = files_dir or (lambda: None)
        self._skills = skills
        self._defects = defects
        self._materials = materials
        self._cancel = threading.Event()
        self._execution = threading.Lock()
        self._tools = {
            constants.TOOL_APPLY_CHANGES: self._apply_changes,
            constants.TOOL_SEARCH_SETTINGS: self._search_settings,
            constants.TOOL_INSPECT_PROFILE: self._inspect_profile,
            constants.TOOL_INSPECT_MATERIAL: self._inspect_material,
            constants.TOOL_INSPECT_SCENE: self._inspect_scene,
            constants.TOOL_ANALYZE_GEOMETRY: self._analyze_geometry,
            constants.TOOL_RENDER_SCENE: self._render_scene,
            constants.TOOL_SLICE: self._slice,
            constants.TOOL_READ_DOCUMENT: self._read_document,
            constants.TOOL_LOAD_SKILL: self._load_skill,
            constants.TOOL_LOOKUP_DEFECT: self._lookup_defect,
            constants.TOOL_MATCH_MATERIALS: self._match_materials,
            constants.TOOL_CALCULATE: self._calculate,
            constants.TOOL_GENERATE_CALIBRATION: self._generate_calibration,
            constants.TOOL_CALIBRATION_JOURNAL: self._calibration_journal,
        }

    def cancel(self):
        self._cancel.set()
        self._port.cancel_slice()

    def execute(self, name, arguments, report=None):
        with self._execution:
            self._cancel.clear()
            return self._run(name, arguments or {}, report)

    def _run(self, tool, arguments, report):
        handler = self._tools.get(tool)
        applied = []
        images = []
        try:
            if handler is None:
                raise OperationError(constants.ERR_UNKNOWN_TOOL, "tool %s is not executed by the plugin" % tool)
            result = handler(arguments, report, applied, images)
            return {"ok": True, "result": result, "error": None, "applied": applied, "images": images}
        except OperationError as error:
            return {"ok": False, "result": dict(error.details), "error": error_object(error.code, error.message),
                    "applied": applied, "images": images}
        except Exception as error:
            return {"ok": False, "result": {}, "applied": applied, "images": images,
                    "error": error_object(constants.ERR_OUTCOME_UNKNOWN, "unexpected failure: %s" % error)}

    def _check_cancelled(self):
        if self._cancel.is_set():
            raise OperationError(constants.ERR_CANCELLED, "stopped by the user")

    def _apply_changes(self, arguments, report, applied, images):
        operations = arguments.get("operations")
        problems = validate_operations(operations)
        if problems:
            raise OperationError(constants.ERR_INVALID_ARGUMENTS, "invalid operations", {"problems": problems})
        before = state_summary(self._port.read_state())
        self._port.begin_batch()
        try:
            for index, op in enumerate(operations):
                if self._cancel.is_set():
                    raise OperationError(constants.ERR_CANCELLED, "stopped by the user", {"stopped_at": index})
                result = self._port.apply_operation(op, check=self._check_cancelled)
                applied.append({"index": index, "kind": op["kind"], "result": result})
                if report:
                    report("apply_changes", (index + 1) / float(len(operations)))
        except OperationError as error:
            error.details = dict(error.details, failed_index=len(applied), failed_kind=operations[len(applied)]["kind"],
                                 state=self._port.read_state(), before=before)
            raise
        except Exception as error:
            raise OutcomeUnknown("operation %d (%s) ended unexpectedly: %s" % (
                len(applied), operations[len(applied)]["kind"], error),
                {"failed_index": len(applied), "state": self._port.read_state(), "before": before})
        finally:
            self._port.end_batch()
        return {"before": before, "state": self._port.read_state()}

    def _search_settings(self, arguments, report, applied, images):
        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            raise OperationError(constants.ERR_INVALID_ARGUMENTS, "query required")
        return {"matches": self._port.search_settings(query.strip())}

    def _inspect_profile(self, arguments, report, applied, images):
        return self._port.inspect_profile()

    def _inspect_material(self, arguments, report, applied, images):
        return self._port.inspect_material(arguments.get("material_id"))

    def _inspect_scene(self, arguments, report, applied, images):
        return {"scene_version": self._port.scene_version(), "state": self._port.read_state()}

    def _render_scene(self, arguments, report, applied, images):
        result = dict(self._port.render_scene(arguments.get("view") or "iso"))
        images.append({"mime_type": "image/png", "data": result.pop("png")})
        return result

    def _analyze_geometry(self, arguments, report, applied, images):
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

    def _attachment_path(self, path):
        directory = self._files_dir()
        if directory is None:
            raise OperationError(constants.ERR_NOT_AVAILABLE, "no chat is open")
        if not isinstance(path, str) or not path:
            raise OperationError(constants.ERR_INVALID_ARGUMENTS, "path required")
        root = os.path.realpath(directory)
        target = os.path.realpath(path if os.path.isabs(path) else os.path.join(root, path))
        if os.path.commonpath([root, target]) != root or not os.path.isfile(target):
            raise OperationError(constants.ERR_INVALID_ARGUMENTS, "path must be an attachment of the current chat")
        return target

    def _read_document(self, arguments, report, applied, images):
        result, embedded = read_document(self._attachment_path(arguments.get("path")), arguments.get("start", 0),
                                         arguments.get("max_chars"), arguments.get("sheet"), arguments.get("rows"),
                                         arguments.get("pages"))
        images.extend({"mime_type": item["mime_type"], "data": item["data"]} for item in embedded)
        return result

    def _load_skill(self, arguments, report, applied, images):
        name = arguments.get("name")
        body = self._skills.body(name) if self._skills is not None else None
        if body is None:
            known = ", ".join(self._skills.names()) if self._skills is not None else ""
            raise OperationError(constants.ERR_INVALID_ARGUMENTS, "unknown skill %s; skills: %s" % (name, known))
        return {"name": name, "instructions": body}

    def _lookup_defect(self, arguments, report, applied, images):
        if self._defects is None:
            raise OperationError(constants.ERR_NOT_AVAILABLE, "the defect guide is not loaded")
        return self._defects.lookup(arguments.get("query"), arguments.get("defect_id"))

    def _match_materials(self, arguments, report, applied, images):
        if self._materials is None:
            raise OperationError(constants.ERR_NOT_AVAILABLE, "the material table is not loaded")
        return self._materials.match(arguments.get("requirements"))

    def _calculate(self, arguments, report, applied, images):
        return calculate(arguments.get("formula"), arguments.get("inputs"))

    def _generate_calibration(self, arguments, report, applied, images):
        return generate(arguments.get("kind"), arguments.get("params") or {}, self._files_dir(), self._port.setting_facts)

    def _calibration_journal(self, arguments, report, applied, images):
        return run_journal(arguments, self._files_dir(), self._port.setting_facts)

    def _fingerprint(self):
        state = dict(self._port.read_state())
        for volatile in ("slice_state", "errors"):
            state.pop(volatile, None)
        return json.dumps(state, sort_keys=True, default=str)

    def _slice(self, arguments, report, applied, images):
        directory = self._output_dir()
        if directory is None:
            raise OperationError(constants.ERR_NOT_AVAILABLE, "no chat is open to store the result")
        version = self._port.scene_version()
        before = self._fingerprint()

        def check():
            self._check_cancelled()
            if self._fingerprint() != before:
                raise OperationError(constants.ERR_STALE_RESULT, "the scene changed while slicing; result discarded")

        check()
        summary = self._port.slice(report or (lambda stage, fraction: None), check)
        check()
        files = self._port.export_artifacts(directory, check)
        return {"slice": summary, "files": files, "scene_version": version}
