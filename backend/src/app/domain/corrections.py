from dataclasses import dataclass

from app.domain.jsonvalue import JsonObject


@dataclass(frozen=True, slots=True)
class CorrectionState:
    key: str | None = None
    failures: int = 0


def operation_key(tool: str, arguments: JsonObject, applied_count: int) -> str:
    if tool != "apply_changes":
        return tool
    operations = arguments.get("operations")
    if not isinstance(operations, list) or applied_count >= len(operations):
        return tool
    operation = operations[applied_count]
    if not isinstance(operation, dict):
        return tool
    target = operation.get("key") or operation.get("object_id") or operation.get("profile_id")
    return f"{tool}:{operation.get('kind')}:{target}"


def register_outcome(state: CorrectionState, key: str, *, succeeded: bool) -> CorrectionState:
    if succeeded:
        return CorrectionState() if state.key == key else state
    if state.key == key:
        return CorrectionState(key=key, failures=state.failures + 1)
    return CorrectionState(key=key, failures=1)


def limit_reached(state: CorrectionState, limit: int) -> bool:
    return state.failures >= limit
