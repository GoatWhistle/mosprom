from dataclasses import dataclass, field
from datetime import datetime

from app.domain.jsonvalue import JsonObject
from app.domain.run import RunState


@dataclass(frozen=True, slots=True, kw_only=True)
class RunDTO:
    id: str
    conversation_id: str
    instance_id: str
    state: RunState
    requirements_ready: bool = False
    requirements_summary: str | None = None
    correction_key: str | None = None
    correction_failures: int = 0
    help_required: bool = False
    steps: int = 0
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class RunEventDTO:
    id: int
    run_id: str
    conversation_id: str
    kind: str
    payload: JsonObject
    created_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class QuestionBatchDTO:
    id: str
    run_id: str
    call_id: str
    questions: tuple[str, ...]
    answer: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class TranscriptEntry:
    role: str
    content: str = ""
    tool_calls: tuple[JsonObject, ...] = ()
    tool_call_id: str | None = None
    attachment_ids: tuple[str, ...] = ()
    extra: JsonObject = field(default_factory=dict)
