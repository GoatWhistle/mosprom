import hashlib
import json
from enum import StrEnum

from app.domain.jsonvalue import JsonObject


class Mode(StrEnum):
    AUTO = "auto"
    ASK = "ask"


class BatchStatus(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CLARIFIED = "clarified"
    STALE = "stale"
    EXECUTED = "executed"


class Decision(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"
    CLARIFY = "clarify"


def batch_hash(operations: list[JsonObject]) -> str:
    canonical = json.dumps(operations, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def permits_execution(
    *,
    mode: Mode,
    operations: list[JsonObject],
    scene_version: int,
    batch_status: BatchStatus | None,
    batch_hash_value: str | None,
    batch_scene_version: int | None,
) -> bool:
    if batch_status is BatchStatus.EXECUTED or batch_status is BatchStatus.STALE:
        return False
    if batch_scene_version is not None and batch_scene_version != scene_version:
        return False
    if batch_hash_value is not None and batch_hash_value != batch_hash(operations):
        return False
    if mode is Mode.AUTO:
        return True
    return (
        batch_status is BatchStatus.ACCEPTED
        and batch_hash_value == batch_hash(operations)
        and batch_scene_version == scene_version
    )
