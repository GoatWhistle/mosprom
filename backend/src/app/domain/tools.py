import json
from dataclasses import dataclass
from functools import cache
from importlib import resources

from app.domain.errors import InvalidRequest
from app.domain.jsonvalue import JsonObject, JsonValue

READ_ONLY_TOOLS = frozenset(
    {"search_settings", "inspect_profile", "inspect_material", "analyze_geometry", "render_scene"}
)
MUTATING_TOOLS = frozenset({"apply_changes", "slice"})
INTERVIEW_BLOCKED_TOOLS = MUTATING_TOOLS
INTERACTIVE_TOOLS = frozenset({"ask_user"})


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    input_schema: JsonObject


@cache
def load_catalog() -> tuple[ToolSpec, ...]:
    raw = resources.files("app.domain").joinpath("tools.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    return tuple(
        ToolSpec(
            name=item["name"],
            description=item["description"],
            input_schema=item["input_schema"],
        )
        for item in data["tools"]
    )


def find_tool(name: str) -> ToolSpec | None:
    return next((tool for tool in load_catalog() if tool.name == name), None)


def mcp_catalog() -> list[JsonObject]:
    return [
        {"name": tool.name, "description": tool.description, "inputSchema": tool.input_schema}
        for tool in load_catalog()
    ]


def validate_schema(value: JsonValue, schema: JsonObject, path: str = "$") -> None:
    expected = schema.get("type")
    if expected is not None and not _matches_type(value, str(expected)):
        raise InvalidRequest(f"{path} must be of type {expected}")
    allowed = schema.get("enum")
    if isinstance(allowed, list) and value not in allowed:
        raise InvalidRequest(f"{path} must be one of {allowed}")
    if isinstance(value, dict):
        required = schema.get("required")
        for name in required if isinstance(required, list) else []:
            if name not in value:
                raise InvalidRequest(f"{path}.{name} is required")
        properties = schema.get("properties")
        if isinstance(properties, dict):
            for name, item in value.items():
                sub = properties.get(name)
                if isinstance(sub, dict):
                    validate_schema(item, sub, f"{path}.{name}")
    if isinstance(value, list):
        _validate_array(value, schema, path)


def _validate_array(value: list[JsonValue], schema: JsonObject, path: str) -> None:
    minimum = schema.get("minItems")
    maximum = schema.get("maxItems")
    if isinstance(minimum, int) and len(value) < minimum:
        raise InvalidRequest(f"{path} needs at least {minimum} items")
    if isinstance(maximum, int) and len(value) > maximum:
        raise InvalidRequest(f"{path} allows at most {maximum} items")
    items = schema.get("items")
    if isinstance(items, dict):
        for index, item in enumerate(value):
            validate_schema(item, items, f"{path}[{index}]")


def _matches_type(value: JsonValue, expected: str) -> bool:
    match expected:
        case "object":
            return isinstance(value, dict)
        case "array":
            return isinstance(value, list)
        case "string":
            return isinstance(value, str)
        case "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        case "number":
            return isinstance(value, int | float) and not isinstance(value, bool)
        case "boolean":
            return isinstance(value, bool)
    return True
