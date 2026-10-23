from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from app.domain.confirmation import BatchStatus
from app.domain.jsonvalue import JsonObject


class CallStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    COMPLETED = "completed"
    FAILED = "failed"
    OUTCOME_UNKNOWN = "outcome_unknown"

    @property
    def finished(self) -> bool:
        return self in {CallStatus.COMPLETED, CallStatus.FAILED, CallStatus.OUTCOME_UNKNOWN}


@dataclass(frozen=True, slots=True, kw_only=True)
class ToolCallDTO:
    call_id: str
    run_id: str
    llm_call_id: str
    tool: str
    arguments: JsonObject
    expected_scene_version: int
    status: CallStatus
    batch_id: str | None = None
    result: JsonObject | None = None
    error: JsonObject | None = None
    applied: tuple[JsonObject, ...] = ()
    scene_version: int | None = None
    created_at: datetime
    finished_at: datetime | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ToolOutcome:
    call_id: str
    ok: bool
    scene_version: int | None
    result: JsonObject
    error: JsonObject | None
    applied: tuple[JsonObject, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True, kw_only=True)
class ChangeBatchDTO:
    id: str
    run_id: str
    call_id: str
    content_hash: str
    scene_version: int
    operations: tuple[JsonObject, ...]
    explanation: str
    status: BatchStatus
    decision_text: str | None = None
    created_at: datetime
