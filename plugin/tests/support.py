import os
import sys

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)

from Brim.execution.errors import OperationError
from Brim.protocol import constants


class FakePort(object):
    def __init__(self):
        self.version = 1
        self.applied = []
        self.fail_on = None
        self.batches = 0
        self.slices = 0
        self.exports = 0
        self.cancelled = 0
        self.bump_on_slice = False
        self.export_dir = None
        self.state = {"printer": {"name": "fake"}, "objects": []}
        self.facts = {"material_bed_temperature": {"value": 40, "minimum_value": 0, "maximum_value": 120,
                                                   "minimum_value_warning": 20, "maximum_value_warning": 110,
                                                   "unit": "°C"}}

    def scene_version(self):
        return self.version

    def read_state(self):
        return dict(self.state)

    def printer_summary(self):
        return {"name": "fake", "modes": list(constants.PRINT_MODES)}

    def begin_batch(self):
        self.batches += 1

    def end_batch(self):
        self.batches -= 1

    def apply_operation(self, op, check=None):
        if check:
            check()
        if self.fail_on == op["kind"]:
            raise OperationError(constants.ERR_OPERATION_FAILED, "boom")
        self.applied.append(op)
        self.version += 1
        return {"done": op["kind"]}

    def search_settings(self, query):
        return [{"key": "layer_height", "query": query}]

    def inspect_profile(self):
        return {"profile": "fine"}

    def inspect_material(self, material_id):
        return {"material": material_id}

    def render_scene(self, view):
        return {"view": view, "png": b"\x89PNG-fake"}

    def setting_facts(self, key, extruder=None):
        return self.facts.get(key)

    def snapshot(self):
        return self.version, dict(self.state, settings=[{"category": "material", "settings": ["material_bed_temperature = 40"]}])

    def mesh_snapshot(self, object_id):
        if object_id != "obj-1":
            return None
        return cube_mesh()

    def slice(self, report, check=None):
        if check:
            check()
        self.slices += 1
        report("slicing", 0.5)
        if self.bump_on_slice:
            self.version += 1
            self.state = dict(self.state, objects=[{"id": "moved"}])
        return {"print_time_seconds": 600}

    def export_artifacts(self, directory, check=None):
        if check:
            check()
        self.exports += 1
        paths = {}
        for kind, name, payload in (("gcode", "result.gcode", b"G1 X0\n" * 10), ("3mf", "result.3mf", b"PK" + b"x" * 100)):
            paths[kind] = os.path.join(directory, name)
            with open(paths[kind], "wb") as handle:
                handle.write(payload)
        return paths

    def cancel_slice(self):
        self.cancelled += 1


def cube_mesh(size=10.0):
    s = size
    vertices = [(0, 0, 0), (s, 0, 0), (s, s, 0), (0, s, 0), (0, 0, s), (s, 0, s), (s, s, s), (0, s, s)]
    triangles = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
                 (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return {"vertices": [tuple(float(i) for i in v) for v in vertices], "triangles": triangles}
