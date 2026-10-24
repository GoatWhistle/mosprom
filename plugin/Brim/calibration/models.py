import math
import os
import uuid

from ..execution.errors import OperationError
from ..protocol import constants
from .figure import calibration_figure, checked_zones
from .mesh import bounds, box, circle, prism, square_with_hole, write_stl

DEFAULT_ANGLES = [30, 40, 50, 60, 70]
DEFAULT_BRIDGES = [10, 20, 30, 40]
DEFAULT_HOLES = [3.0, 4.0, 5.0, 6.0, 8.0]


def _number(params, name, default, low, high):
    value = params.get(name, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
        raise OperationError(constants.ERR_INVALID_ARGUMENTS, "%s must be a number in %s..%s" % (name, low, high))
    return float(value)


def _list(params, name, default, low, high):
    values = params.get(name, default)
    if not isinstance(values, list) or not values or len(values) > 8 or not all(
            isinstance(item, (int, float)) and not isinstance(item, bool) and low <= item <= high for item in values):
        raise OperationError(constants.ERR_INVALID_ARGUMENTS, "%s must be 1..8 numbers in %s..%s" % (name, low, high))
    return [float(item) for item in values]


def cube(params):
    size = _number(params, "size_mm", 20, 5, 100)
    return box(0, 0, 0, size, size, size), {"checks": "X/Y/Z dimensions, first layer, walls, top surface",
                                            "expected_mm": [size, size, size]}


def overhang_test(params):
    angles = _list(params, "angles_deg", DEFAULT_ANGLES, 10, 80)
    height = _number(params, "height_mm", 15, 5, 50)
    width, depth, gap = 5.0, 8.0, 3.0
    triangles = []
    features = []
    for index, angle in enumerate(angles):
        y = index * (depth + gap)
        reach = height * math.tan(math.radians(angle))
        triangles += prism([(0, 0), (width, 0), (width + reach, height), (0, height)], y, y + depth, plane="xz")
        features.append({"y_mm": [round(y, 1), round(y + depth, 1)], "overhang_deg_from_vertical": angle})
    return triangles, {"checks": "the steepest overhang printed cleanly without supports; cooling",
                       "features": features}


def bridge_test(params):
    lengths = _list(params, "lengths_mm", DEFAULT_BRIDGES, 5, 80)
    height = _number(params, "height_mm", 8, 3, 30)
    pillar, thickness, depth, gap = 5.0, 1.0, 8.0, 3.0
    triangles = []
    features = []
    for index, length in enumerate(lengths):
        y = index * (depth + gap)
        profile = [(0, 0), (pillar, 0), (pillar, height), (pillar + length, height), (pillar + length, 0),
                   (2 * pillar + length, 0), (2 * pillar + length, height + thickness), (0, height + thickness)]
        triangles += prism(profile, y, y + depth, plane="xz")
        features.append({"y_mm": [round(y, 1), round(y + depth, 1)], "bridge_mm": length})
    return triangles, {"checks": "sagging and strand gaps under each bridge; bridge speed, fan and flow",
                       "features": features}


def stringing_towers(params):
    distance = _number(params, "distance_mm", 30, 10, 100)
    height = _number(params, "height_mm", 30, 10, 100)
    radius = 4.0
    triangles = prism(circle(0, 0, radius), 0, height) + prism(circle(distance, 0, radius), 0, height)
    return triangles, {"checks": "threads between the towers; retraction distance, speed, temperature, travel",
                       "towers": 2, "distance_mm": distance}


def hole_tolerance(params):
    diameters = _list(params, "diameters_mm", DEFAULT_HOLES, 1, 30)
    thickness = _number(params, "thickness_mm", 5, 2, 20)
    triangles = []
    features = []
    x = 0.0
    for diameter in diameters:
        size = diameter + 6.0
        center = x + size / 2.0
        triangles += square_with_hole(center, size / 2.0, size, diameter / 2.0, 0, thickness)
        features.append({"x_mm": round(center, 2), "nominal_diameter_mm": diameter})
        x += size + 2.0
    return triangles, {"checks": "measure each hole; feed the result to calculate hole_compensation",
                       "features": features}


KINDS = {"cube": cube, "overhang_test": overhang_test, "bridge_test": bridge_test,
         "stringing_towers": stringing_towers, "hole_tolerance": hole_tolerance,
         "calibration_figure": calibration_figure}


def generate(kind, params, directory, facts=None):
    builder = KINDS.get(kind)
    if builder is None:
        raise OperationError(constants.ERR_INVALID_ARGUMENTS, "unknown kind %s; kinds: %s" % (kind, ", ".join(sorted(KINDS))))
    if directory is None:
        raise OperationError(constants.ERR_NOT_AVAILABLE, "no chat is open to store the model")
    triangles, details = builder(params if isinstance(params, dict) else {})
    if "zones" in details:
        zones, unknown = checked_zones(details["zones"], facts)
        details = dict(details, zones=zones, unknown_keys=unknown)
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, "calibration-%s-%s.stl" % (kind, uuid.uuid4().hex[:8]))
    write_stl(path, triangles, "brim %s" % kind)
    return dict(details, kind=kind, path=path, triangles=len(triangles), bounds_mm=bounds(triangles),
                next_step="import it with apply_changes import_model using this path")
