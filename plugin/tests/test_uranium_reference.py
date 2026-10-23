import math
import os
import sys
import unittest

from tests import support
from Brim.slicer import frames

REFERENCE = os.environ.get("BRIM_URANIUM_PATH", "")


def load_uranium():
    if not REFERENCE or not os.path.isdir(os.path.join(REFERENCE, "UM")):
        raise unittest.SkipTest("set BRIM_URANIUM_PATH to a Uranium 3.6 checkout")
    try:
        import numpy
    except ImportError:
        raise unittest.SkipTest("numpy is not installed")
    sys.path.insert(0, REFERENCE)
    try:
        from UM.Math.Quaternion import Quaternion
        from UM.Math.Vector import Vector
    except Exception as error:
        raise unittest.SkipTest("Uranium math is not importable: %s" % error)
    finally:
        sys.path.remove(REFERENCE)
    return numpy, Quaternion, Vector


def build_matrix(angles):
    return frames.euler_matrix(angles)


class UraniumConventionTests(unittest.TestCase):
    def rotate_in_scene(self, angles, build_vector):
        numpy, Quaternion, Vector = load_uranium()
        q = frames.build_rotation_to_scene_quaternion(angles)
        scene_vector = frames.build_to_scene(build_vector)
        rotated = Quaternion(q[0], q[1], q[2], q[3]).rotate(Vector(*scene_vector))
        return frames.scene_to_build(tuple(float(item) for item in rotated.getData()))

    def expected_in_build(self, angles, vector):
        matrix = build_matrix(angles)
        return tuple(sum(matrix[i][j] * vector[j] for j in range(3)) for i in range(3))

    def test_uranium_quaternion_matches_build_frame_euler_rotation(self):
        for angles in ((0, 0, 90), (90, 0, 0), (0, 90, 0), (30, 40, 50), (-70, 15, 120)):
            for vector in ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 2.0, 3.0)):
                actual = self.rotate_in_scene(angles, vector)
                expected = self.expected_in_build(angles, vector)
                for a, b in zip(actual, expected):
                    self.assertAlmostEqual(a, b, places=4, msg="%s %s" % (angles, vector))

    def test_orientation_read_back_from_uranium_quaternion(self):
        numpy, Quaternion, Vector = load_uranium()
        for angles in ((20.0, 30.0, 40.0), (0.0, 0.0, 90.0), (-70.0, 15.0, 120.0)):
            q = frames.build_rotation_to_scene_quaternion(angles)
            stored = Quaternion(q[0], q[1], q[2], q[3])
            back = frames.scene_quaternion_to_build_euler((stored.x, stored.y, stored.z, stored.w))
            for expected, actual in zip(angles, back):
                self.assertAlmostEqual(math.sin(math.radians(expected)), math.sin(math.radians(actual)), places=4)


if __name__ == "__main__":
    unittest.main()
