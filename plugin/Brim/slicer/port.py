import threading

from ..execution.errors import OperationError
from ..protocol import constants
from . import frames
from .project_archive import verify_workspace


class SlicerPort(object):
    def __init__(self, host, access, state, scene_ops, settings_ops, catalog, slicing, renderer, main, digest):
        self._h = host
        self._digest = digest
        self._access = access
        self._state = state
        self._scene_ops = scene_ops
        self._settings_ops = settings_ops
        self._catalog = catalog
        self._slicing = slicing
        self._renderer = renderer
        self._main = main
        self._version = 1
        self._lock = threading.Lock()
        self._listeners = []
        self._locked = False
        self._handlers = {
            "select_mode": settings_ops.select_mode,
            "select_profile": settings_ops.select_profile,
            "select_material": settings_ops.select_material,
            "set_global_setting": settings_ops.set_global,
            "set_extruder_setting": settings_ops.set_extruder,
            "reset_overrides": settings_ops.reset_overrides,
            "save_profile": settings_ops.save_profile,
            "transform": scene_ops.transform,
            "duplicate": scene_ops.duplicate,
            "arrange": scene_ops.arrange,
            "delete": scene_ops.delete,
            "set_object_extruder": scene_ops.set_object_extruder,
            "import_model": scene_ops.import_model,
            "open_3mf": scene_ops.open_3mf,
        }

    def add_change_listener(self, listener):
        self._listeners.append(listener)

    def watch(self):
        failures = []
        scene = self._h.scene()
        application = self._h.application
        manager = self._h.machine_manager()
        sources = [(scene, "sceneChanged", self._on_scene_changed),
                   (application, "globalContainerStackChanged", self._settings_changed)]
        for name in ("activeMaterialChanged", "activeQualityChanged", "activeVariantChanged", "globalValueChanged",
                     "activeStackValueChanged", "extruderChanged"):
            sources.append((manager, name, self._settings_changed))
        sources.append((application.getMaterialManager(), "materialsUpdated", self._settings_changed))
        for owner, name, handler in sources:
            signal = getattr(owner, name, None)
            if signal is None:
                failures.append(name)
                continue
            signal.connect(handler)
        return failures

    def _on_scene_changed(self, source):
        if not isinstance(source, self._h.SceneNode):
            return
        if source == self._h.scene().getRoot() or source.callDecoration("isGroup") or source.callDecoration("isSliceable"):
            self._bump()

    def _settings_changed(self, *args):
        self._digest.invalidate()
        self._bump()

    def _bump(self, *args):
        with self._lock:
            self._version += 1
        for listener in self._listeners:
            listener()

    def snapshot(self):
        return self._main.call(lambda: (self.scene_version(), self._snapshot_state()))

    def _snapshot_state(self):
        state = self._state.read()
        try:
            state["settings"] = self._digest.read()
        except Exception as error:
            state["errors"].append("settings unavailable: %s" % error)
        return state

    def scene_version(self):
        with self._lock:
            return self._version

    def read_state(self):
        return self._main.call(self._state.read)

    def printer_summary(self):
        return self._main.call(self._state.printer_summary)

    def begin_batch(self):
        self._slicing.begin_batch()

    def end_batch(self):
        self._slicing.end_batch()

    def lock_changes(self, locked):
        self._locked = bool(locked)

    def _ensure_unlocked(self):
        if self._locked:
            raise OperationError(constants.ERR_NOT_AVAILABLE, "the project is being switched")

    def scene_is_empty(self):
        return self._scene_ops.count() == 0

    def save_workspace(self, path):
        self._slicing.write_project(path)
        verify_workspace(path)

    def load_workspace(self, path):
        verify_workspace(path)
        self._scene_ops.open_3mf({"path": path, "import_as": "restore_project"})
        self._digest.invalidate()

    def clear_workspace(self):
        removed = self._scene_ops.clear()
        self._settings_ops.reset_overrides({})
        self._digest.invalidate()
        return removed

    def apply_operation(self, op, check=None):
        self._ensure_unlocked()
        handler = self._handlers.get(op["kind"])
        if handler is None:
            raise OperationError(constants.ERR_INVALID_ARGUMENTS, "unknown operation kind %s" % op["kind"])

        def guard():
            if check is not None:
                check()

        try:
            return handler(op, guard=guard)
        finally:
            self._digest.invalidate()

    def setting_facts(self, key, extruder=None):
        return self._main.call(self._digest.facts, key, extruder)

    def search_settings(self, query):
        return self._catalog.search_settings(query)

    def inspect_profile(self):
        return self._catalog.inspect_profile()

    def inspect_material(self, material_id):
        return self._catalog.inspect_material(material_id)

    def render_scene(self, view):
        return self._renderer.render(view)

    def mesh_snapshot(self, object_id):
        return self._main.call(self._mesh, object_id)

    def _mesh(self, object_id):
        node = self._access.find(object_id)
        if node is None:
            return None
        mesh = node.getMeshDataTransformed()
        if mesh is None:
            return None
        raw = mesh.getVertices()
        vertices = [frames.scene_to_build((float(row[0]), float(row[1]), float(row[2]))) for row in raw]
        if mesh.hasIndices():
            triangles = [(int(row[0]), int(row[1]), int(row[2])) for row in mesh.getIndices()]
        else:
            triangles = [(i, i + 1, i + 2) for i in range(0, len(vertices) - 2, 3)]
        return {"vertices": vertices, "triangles": triangles}

    def slice(self, report, check=None):
        self._ensure_unlocked()
        return self._slicing.slice(report, check)

    def export_artifacts(self, directory, check=None):
        return self._slicing.export(directory, check)

    def cancel_slice(self):
        self._slicing.cancel()
