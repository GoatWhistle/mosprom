from app.domain.errors import InvalidRequest
from app.domain.jsonvalue import JsonObject, JsonValue
from app.domain.tools import find_tool, validate_schema

REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "select_mode": ("mode",),
    "select_profile": ("profile_id",),
    "select_material": ("material_id", "extruder"),
    "set_global_setting": ("key", "value"),
    "set_extruder_setting": ("key", "value", "extruder"),
    "reset_overrides": ("keys",),
    "import_model": ("attachment_id",),
    "open_3mf": ("attachment_id", "import_as"),
    "transform": ("object_id", "frame"),
    "duplicate": ("object_id", "count"),
    "arrange": (),
    "delete": ("object_ids",),
    "save_profile": ("name",),
}
TRANSFORM_FIELDS = ("position_mm", "rotation_deg", "scale")


def validate_tool_arguments(tool: str, arguments: JsonValue) -> JsonObject:
    spec = find_tool(tool)
    if spec is None:
        raise InvalidRequest(f"Unknown tool {tool!r}")
    if not isinstance(arguments, dict):
        raise InvalidRequest("Tool arguments must be an object")
    validate_schema(arguments, spec.input_schema)
    if tool == "apply_changes":
        for index, operation in enumerate(_operations(arguments)):
            _validate_operation(index, operation)
    return arguments


def operations_of(arguments: JsonObject) -> list[JsonObject]:
    return _operations(arguments)


def _operations(arguments: JsonObject) -> list[JsonObject]:
    raw = arguments.get("operations")
    if not isinstance(raw, list):
        raise InvalidRequest("operations must be a list")
    return [item for item in raw if isinstance(item, dict)]


def _validate_operation(index: int, operation: JsonObject) -> None:
    kind = str(operation["kind"])
    for name in REQUIRED_FIELDS[kind]:
        if name not in operation:
            raise InvalidRequest(f"operations[{index}] {kind} requires {name}")
    if kind == "transform":
        if not any(name in operation for name in TRANSFORM_FIELDS):
            raise InvalidRequest(
                f"operations[{index}] transform needs a position, rotation or scale"
            )
        if "rotation_deg" in operation and "rotation_center" not in operation:
            raise InvalidRequest(f"operations[{index}] transform needs rotation_center")
