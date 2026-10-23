import os
import threading

from ..execution.errors import OperationError, OutcomeUnknown
from ..protocol import constants
from . import frames

LOAD_TIMEOUT = 300.0
JOB_TIMEOUT = 300.0


class SceneOperations(object):
    def __init__(self, host, access, main):
        self._h = host
        self._access = access
        self._main = main

    def transform(self, op):
        node = self._access.require(op["object_id"])
        center = op.get("rotation_center", "bbox_center")
        self._main.call(self._transform_on_main, node, op, center)
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

    def delete(self, op):
        nodes = [self._access.require(item) for item in op["object_ids"]]
        removed = [self._access.id_of(node) for node in nodes]

        def run():
            group = self._h.GroupedOperation()
            for node in nodes:
                group.addOperation(self._h.RemoveSceneNodeOperation(node))
            group.push()

        self._main.call(run)
        return {"removed": removed}

    def duplicate(self, op):
        node = self._access.require(op["object_id"])
        known = set(self._access.id_of(item) for item in self._main.call(self._access.objects))
        count = op.get("count", 1)
        self._run_job(lambda: self._h.MultiplyObjectsJob([node], count, 8))
        created = self._main.call(self._new_ids, known)
        if len(created) < count:
            raise OperationError(constants.ERR_OPERATION_FAILED,
                                 "only %d of %d copies fit on the build plate" % (len(created), count),
                                 {"created": created})
        return {"created": created}

    def arrange(self, op):
        ids = op.get("object_ids")
        everything = self._main.call(self._access.objects)
        chosen = [self._access.require(item) for item in ids] if ids else list(everything)
        fixed = [node for node in everything if node not in chosen]
        self._run_job(lambda: self._h.ArrangeObjectsJob(chosen, fixed, 8))
        return {"arranged": [self._access.id_of(node) for node in chosen]}

    def import_model(self, op):
        path = op["path"]
        known = set(self._access.id_of(item) for item in self._main.call(self._access.objects))
        self._load_file(path)
        created = self._main.call(self._new_ids, known)
        if not created:
            raise OperationError(constants.ERR_OPERATION_FAILED, "no objects appeared after importing %s" % os.path.basename(path))
        return {"created": created}

    def open_3mf(self, op):
        if op["import_as"] == "import_geometry":
            return self.import_model(op)
        application = self._h.application
        handler = application.getWorkspaceFileHandler()
        done = threading.Event()

        def on_loaded(*args):
            done.set()

        self._main.call(application.workspaceLoaded.connect, on_loaded)
        try:
            self._main.call(handler.readLocalFile, self._h.QUrl.fromLocalFile(op["path"]))
            finished = done.wait(LOAD_TIMEOUT)
        finally:
            self._main.call(application.workspaceLoaded.disconnect, on_loaded)
        if not finished:
            raise OutcomeUnknown("project dialog was not completed within %.0f s" % LOAD_TIMEOUT,
                                 {"note": "restore_project asks the user to confirm conflicts in the slicer window"})
        return {"restored": True}

    def _new_ids(self, known):
        return [self._access.id_of(node) for node in self._access.objects()
                if self._access.id_of(node) not in known]

    def _load_file(self, path):
        application = self._h.application
        done = threading.Event()

        def on_completed(*args):
            done.set()

        self._main.call(application.fileCompleted.connect, on_completed)
        try:
            self._main.call(application.readLocalFile, self._h.QUrl.fromLocalFile(path))
            finished = done.wait(LOAD_TIMEOUT)
        finally:
            self._main.call(application.fileCompleted.disconnect, on_completed)
        if not finished:
            raise OutcomeUnknown("file import did not finish within %.0f s" % LOAD_TIMEOUT)
        self._main.call(lambda: None)

    def _run_job(self, make_job):
        done = threading.Event()

        def on_finished(finished_job):
            done.set()

        def start():
            job = make_job()
            job.finished.connect(on_finished)
            job.start()
            return job

        job = self._main.call(start)
        finished = done.wait(JOB_TIMEOUT)
        self._main.call(job.finished.disconnect, on_finished)
        if not finished:
            raise OutcomeUnknown("slicer job did not finish within %.0f s" % JOB_TIMEOUT)
        self._main.call(lambda: None)
