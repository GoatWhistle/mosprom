import json
import math
import os
import unittest

from tests import support
from Brim.execution.operations import validate_operations
from Brim.slicer import frames


class CoordinateTests(unittest.TestCase):
    def test_vector_round_trip_is_asymmetric_on_all_axes(self):
        for vector in ((1.0, 2.0, 3.0), (-4.0, 5.5, -6.0)):
            self.assertEqual(frames.build_to_scene(frames.scene_to_build(vector)), vector)
        self.assertEqual(frames.build_to_scene((10.0, 20.0, 30.0)), (10.0, 30.0, -20.0))
        self.assertEqual(frames.scene_to_build((10.0, 30.0, -20.0)), (10.0, 20.0, 30.0))

    def test_rotation_round_trip_for_each_axis_and_combination(self):
        for angles in ((30.0, 0.0, 0.0), (0.0, 40.0, 0.0), (0.0, 0.0, 50.0), (20.0, 30.0, 40.0), (-70.0, 15.0, 120.0)):
            quaternion = frames.build_rotation_to_scene_quaternion(angles)
            back = frames.scene_quaternion_to_build_euler(quaternion)
            for expected, actual in zip(angles, back):
                self.assertAlmostEqual(math.sin(math.radians(expected)), math.sin(math.radians(actual)), places=6)

    def test_rotation_about_build_z_is_rotation_about_scene_y(self):
        quaternion = frames.build_rotation_to_scene_quaternion((0.0, 0.0, 90.0))
        self.assertAlmostEqual(abs(quaternion[1]), math.sqrt(0.5), places=6)
        self.assertAlmostEqual(quaternion[0], 0.0, places=6)
        self.assertAlmostEqual(quaternion[2], 0.0, places=6)

    def test_rotated_x_axis_matches_build_frame(self):
        matrix = frames.quaternion_to_matrix(frames.build_rotation_to_scene_quaternion((0.0, 0.0, 90.0)))
        scene_x = (matrix[0][0], matrix[1][0], matrix[2][0])
        build = frames.scene_to_build(scene_x)
        self.assertAlmostEqual(build[0], 0.0, places=6)
        self.assertAlmostEqual(abs(build[1]), 1.0, places=6)
        self.assertEqual(round(build[1]), 1)


class OperationTests(unittest.TestCase):
    def valid_transform(self, **extra):
        op = {"kind": "transform", "object_id": "obj-1", "frame": "scene", "position_mm": [0, 0, 5]}
        op.update(extra)
        return op

    def test_valid_batch(self):
        batch = [
            {"kind": "select_mode", "mode": "cylindrical"},
            {"kind": "select_profile", "profile_id": "fine"},
            {"kind": "select_material", "material_id": "petg", "extruder": 0},
            {"kind": "set_global_setting", "key": "layer_height", "value": 0.2},
            self.valid_transform(rotation_deg=[0, 90, 0], rotation_center="bbox_center", scale=[1, 1, 2]),
            {"kind": "open_3mf", "path": "/tmp/a.3mf", "import_as": "import_geometry"},
            {"kind": "arrange"},
            {"kind": "delete", "object_ids": ["obj-1"]},
        ]
        self.assertEqual(validate_operations(batch), [])

    def test_rejects_bad_batches(self):
        self.assertTrue(validate_operations([]))
        self.assertTrue(validate_operations(None))
        self.assertTrue(validate_operations([{"kind": "explode"}]))
        self.assertTrue(validate_operations([{"kind": "select_mode", "mode": "5d"}]))
        self.assertTrue(validate_operations([{"kind": "select_material", "material_id": "x", "extruder": -1}]))
        self.assertTrue(validate_operations([self.valid_transform(scale=-1)]))
        self.assertTrue(validate_operations([self.valid_transform(rotation_deg=[0, 0, 1])]))
        self.assertTrue(validate_operations([{"kind": "transform", "object_id": "a", "frame": "scene"}]))
        self.assertTrue(validate_operations([self.valid_transform(frame="build")]))
        self.assertTrue(validate_operations([{"kind": "open_3mf", "path": "/tmp/a.3mf", "import_as": "x"}]))

    def test_every_schema_operation_kind_has_a_check(self):
        from Brim.execution.operations import CHECKS
        from Brim.protocol.tools import load_tools

        schema = [tool for tool in load_tools() if tool["name"] == "apply_changes"][0]["inputSchema"]
        text = json.dumps(schema)
        for kind in CHECKS:
            self.assertIn('"%s"' % kind, text)


class ContractTests(unittest.TestCase):
    def test_ask_user_is_not_an_mcp_tool(self):
        from Brim.protocol.tools import load_tools

        names = [tool["name"] for tool in load_tools()]
        self.assertNotIn("ask_user", names)
        self.assertIn("inspect_scene", names)
        self.assertTrue(all("annotations" in tool for tool in load_tools()))

    def test_python35_syntax(self):
        import re

        banned = [
            (re.compile(r"\bf[\"']"), "f-string"),
            (re.compile(r"^\s*async\s+def", re.M), "async def"),
            (re.compile(r":="), "walrus"),
            (re.compile(r"^\s*\w+\s*:\s*[\w\[\], .]+\s*=\s", re.M), "variable annotation"),
            (re.compile(r"\bnonlocal\b.*\n.*f\""), "nonlocal f"),
        ]
        for root, _, names in os.walk(os.path.join(support.PLUGIN_ROOT, "Brim")):
            for name in names:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(root, name)
                with open(path, encoding="utf-8") as handle:
                    source = handle.read()
                for pattern, label in banned:
                    for match in pattern.finditer(source):
                        line = source[:match.start()].count("\n") + 1
                        text = source.splitlines()[line - 1]
                        if label == "variable annotation" and ("def " in text or "lambda" in text or text.strip().startswith(("if", "for", "elif", "else", "while", "class", "with", "try", "except", "finally"))):
                            continue
                        self.fail("%s in %s:%d: %s" % (label, path, line, text))


if __name__ == "__main__":
    unittest.main()
