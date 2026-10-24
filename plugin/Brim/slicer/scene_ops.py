import os
import threading

from ..execution.errors import OperationError, OutcomeUnknown
from ..protocol import constants
from . import frames

LOAD_TIMEOUT = 120.0
JOB_TIMEOUT = 300.0


class SceneOperations(object):
    def __init__(self, host, access, main):
        self._h = host
        self._access = access
        self._main = main

    def transform(self, op, guard=None):
        return self._main.call(self._transform, op, guard=guard)

    def _transform(self, op):
        node = self._access.require(op["object_id"])
        self._transform_on_main(node, op, op.get("rotation_center", "bbox_center"))
        return self._access.describe(node)

    def _transform_on_main(self, node, op, center):
        h = self._h
        before = self._access.pivot(node, center)
        group = h.GroupedOperation()
        if "scale" in op:
            scale = op["scale"]
            if not isinstance(scale, (list, tuple)):
                scale = (scale, scale, scale)
            group.addOperation(h.SetTransformOperation(node, scale=h.Vector(scale[0], scale[2], scale[1])))
        if "rotation_deg" in op:
            q = frames.build_rotation_to_scene_quaternion(op["rotation_deg"])
            group.addOperation(h.SetTransformOperation(node, orientation=h.Quaternion(q[0], q[1], q[2], q[3])))
        group.push()
        if "scale" in op or "rotation_deg" in op:
            after = self._access.pivot(node, center)
            self._translate(node, [b - a for a, b in zip(after, before)])
        if "position_mm" in op:
            current = self._access.pivot(node, "bbox_center")
            self._translate(node, [t - c for t, c in zip(op["position_mm"], current)])

    def _translate(self, node, delta_build):
        if all(abs(item) < 1e-6 for item in delta_build):
            return
        x, y, z = frames.build_to_scene(delta_build)
        self._h.TranslateOperation(node, self._h.Vector(x, y, z)).push()

    def delete(self, op, guard=None):
        def run():
            nodes = [self._access.require(item) for item in op["object_ids"]]
            removed = [self._access.id_of(node) for node in nodes]
            group = self._h.GroupedOperation()
            for node in nodes:
                group.addOperation(self._h.RemoveSceneNodeOperation(node))
            group.push()
            return {"removed": removed}

        return self._main.call(run, guard=guard)

    def set_object_extruder(self, op, guard=None):
        def run():
            node = self._access.require(op["object_id"])
            extruders = self._h.global_stack().extruders
            stack = extruders.get(str(op["extruder"]))
            if stack is None:
                raise OperationError(constants.ERR_OPERATION_FAILED, "extruder %s does not exist" % op["extruder"],
                                     {"extruders": sorted(extruders.keys())})
            node.callDecoration("setActiveExtruder", stack.getId())
            self._h.scene().sceneChanged.emit(node)
            return self._access.describe(node)

        return self._main.call(run, guard=guard)

    def count(self):
        return self._main.call(lambda: len(list(self._access.objects())))

    def clear(self):
        ids = self._main.call(lambda: [self._access.id_of(node) for node in self._access.objects()])
        if ids:
            self.delete({"object_ids": ids})
        return len(ids)

    def duplicate(self, op, guard=None):
        known = self._main.call(self._all_ids)
        count = op.get("count", 1)
        self._run_job(lambda: self._h.MultiplyObjectsJob([self._access.require(op["object_id"])], count, 8), guard)
        created = self._main.call(self._new_ids, known)
        if len(created) < count:
            raise OperationError(constants.ERR_OPERATION_FAILED,
                                 "only %d of %d copies fit on the build plate" % (len(created), count),
                                 {"created": created})
        return {"created": created}

    def arrange(self, op, guard=None):
        arranged = []

        def make_job():
            ids = op.get("object_ids")
            everything = self._access.objects()
            chosen = [self._access.require(item) for item in ids] if ids else everything
            fixed = [node for node in everything if node not in chosen]
            arranged.extend(self._access.id_of(node) for node in chosen)
            return self._h.ArrangeObjectsJob(chosen, fixed, 8)

        self._run_job(make_job, guard)
        return {"arranged": arranged}

    def import_model(self, op, guard=None):
        path = op["path"]
        known = self._main.call(self._all_ids)
        self._load_file(path, guard)
        created = self._main.call(self._new_ids, known)
        if not created:
            raise OperationError(constants.ERR_OPERATION_FAILED, "no objects appeared after importing %s" % os.path.basename(path))
        return {"created": created}

    def open_3mf(self, op, guard=None):
        if op["import_as"] == "import_geometry":
            return self.import_model(op, guard)
        application = self._h.application
        handler = self._main.call(application.getWorkspaceFileHandler)
        done = threading.Event()

        def on_loaded(*args):
            done.set()

        self._main.call(application.workspaceLoaded.connect, on_loaded)
        try:
            self._main.call(handler.readLocalFile, self._h.QUrl.fromLocalFile(op["path"]), guard=guard)
            finished = done.wait(LOAD_TIMEOUT)
        finally:
            self._main.call(application.workspaceLoaded.disconnect, on_loaded)
        if not finished:
            raise OutcomeUnknown("project dialog was not completed within %.0f s" % LOAD_TIMEOUT,
                                 {"note": "restore_project asks the user to confirm conflicts in the slicer window"})
        return {"restored": True}

    def _all_ids(self):
        return set(self._access.id_of(node) for node in self._access.objects())

    def _new_ids(self, known):
        return [self._access.id_of(node) for node in self._access.objects()
                if self._access.id_of(node) not in known]

    def _load_file(self, path, guard=None):
        application = self._h.application
        done = threading.Event()

        target = os.path.basename(path)

        def on_completed(name=""):
            if os.path.basename(str(name)) == target:
                done.set()

        self._main.call(application.fileCompleted.connect, on_completed)
        try:
            self._main.call(application.readLocalFile, self._h.QUrl.fromLocalFile(path), guard=guard)
            finished = done.wait(LOAD_TIMEOUT)
        finally:
            self._main.call(application.fileCompleted.disconnect, on_completed)
        if not finished:
            raise OutcomeUnknown("file import did not finish within %.0f s" % LOAD_TIMEOUT,
                                 {"note": "the slicer emits no completion signal when a file cannot be read"})
        self._main.call(lambda: None)

    def _run_job(self, make_job, guard=None):
        done = threading.Event()

        def on_finished(finished_job):
            done.set()

        def start():
            job = make_job()
            job.finished.connect(on_finished)
            job.start()
            return job

        job = self._main.call(start, guard=guard)
        finished = done.wait(JOB_TIMEOUT)
        self._main.call(job.finished.disconnect, on_finished)
        if not finished:
            raise OutcomeUnknown("slicer job did not finish within %.0f s" % JOB_TIMEOUT)
        self._main.call(lambda: None)
