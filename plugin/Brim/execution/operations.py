from ..protocol import constants

FRAME_SCENE = "scene"
ROTATION_CENTERS = ("bbox_center", "bbox_bottom_center", "origin")
THREEMF_MODES = ("restore_project", "import_geometry")
MODEL_EXTENSIONS = (".stl", ".obj", ".3mf")


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _vector3(value):
    return isinstance(value, (list, tuple)) and len(value) == 3 and all(_is_number(item) for item in value)


def _index(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _text(value):
    return isinstance(value, str) and value != ""


def _check_select_mode(op):
    return [] if op.get("mode") in constants.PRINT_MODES else ["mode must be one of %s" % ", ".join(constants.PRINT_MODES)]


def _check_select_profile(op):
    return [] if _text(op.get("profile_id")) else ["profile_id required"]


def _check_select_material(op):
    problems = [] if _text(op.get("material_id")) else ["material_id required"]
    if not _index(op.get("extruder")):
        problems.append("extruder must be a non-negative integer")
    return problems


def _check_setting(op):
    problems = []
    if not _text(op.get("key")):
        problems.append("key required")
    if "value" not in op:
        problems.append("value required")
    return problems


def _check_extruder_setting(op):
    problems = _check_setting(op)
    if not _index(op.get("extruder")):
        problems.append("extruder must be a non-negative integer")
    return problems


def _check_reset(op):
    keys = op.get("keys")
    if keys is not None and not (isinstance(keys, list) and all(_text(item) for item in keys)):
        return ["keys must be a list of setting keys"]
    return []


def _check_import(op):
    if not _text(op.get("path")):
        return ["path required"]
    return []


def _check_open_3mf(op):
    problems = _check_import(op)
    if op.get("import_as") not in THREEMF_MODES:
        problems.append("import_as must be restore_project or import_geometry")
    return problems


def _check_transform(op):
    problems = []
    if not _text(op.get("object_id")):
        problems.append("object_id required")
    has_change = False
    if "position_mm" in op:
        has_change = True
        if not _vector3(op["position_mm"]):
            problems.append("position_mm must be [x, y, z] in millimetres")
    if "rotation_deg" in op:
        has_change = True
        if not _vector3(op["rotation_deg"]):
            problems.append("rotation_deg must be [rx, ry, rz] in degrees")
        if op.get("rotation_center") not in ROTATION_CENTERS:
            problems.append("rotation_center must be one of %s" % ", ".join(ROTATION_CENTERS))
    if "scale" in op:
        has_change = True
        scale = op["scale"]
        if not (_is_number(scale) and scale > 0 or _vector3(scale) and all(item > 0 for item in scale)):
            problems.append("scale must be a positive number or [sx, sy, sz]")
    if not has_change:
        problems.append("position_mm, rotation_deg or scale required")
    if op.get("frame") != FRAME_SCENE:
        problems.append("frame must be scene")
    return problems


def _check_duplicate(op):
    problems = [] if _text(op.get("object_id")) else ["object_id required"]
    count = op.get("count", 1)
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        problems.append("count must be a positive integer")
    return problems


def _check_arrange(op):
    ids = op.get("object_ids")
    if ids is not None and not (isinstance(ids, list) and all(_text(item) for item in ids)):
        return ["object_ids must be a list of ids"]
    return []


def _check_delete(op):
    ids = op.get("object_ids")
    if not (isinstance(ids, list) and ids and all(_text(item) for item in ids)):
        return ["object_ids must be a non-empty list"]
    return []


def _check_object_extruder(op):
    problems = [] if _text(op.get("object_id")) else ["object_id required"]
    if not _index(op.get("extruder")):
        problems.append("extruder must be a non-negative integer")
    return problems


def _check_save_profile(op):
    return [] if _text(op.get("name")) else ["name required"]


CHECKS = {
    "select_mode": _check_select_mode,
    "select_profile": _check_select_profile,
    "select_material": _check_select_material,
    "set_global_setting": _check_setting,
    "set_extruder_setting": _check_extruder_setting,
    "reset_overrides": _check_reset,
    "import_model": _check_import,
    "open_3mf": _check_open_3mf,
    "transform": _check_transform,
    "duplicate": _check_duplicate,
    "arrange": _check_arrange,
    "delete": _check_delete,
    "set_object_extruder": _check_object_extruder,
    "save_profile": _check_save_profile,
}


def validate_operations(operations):
    if not isinstance(operations, list) or not operations:
        return [{"index": None, "kind": None, "problems": ["operations must be a non-empty list"]}]
    report = []
    for index, op in enumerate(operations):
        if not isinstance(op, dict):
            report.append({"index": index, "kind": None, "problems": ["operation must be an object"]})
            continue
        kind = op.get("kind")
        check = CHECKS.get(kind)
        if check is None:
            report.append({"index": index, "kind": kind, "problems": ["unknown operation kind"]})
            continue
        problems = check(op)
        if problems:
            report.append({"index": index, "kind": kind, "problems": problems})
    return report
