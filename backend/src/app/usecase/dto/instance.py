from dataclasses import dataclass, field
from datetime import datetime

from app.domain.jsonvalue import JsonObject


@dataclass(frozen=True, slots=True, kw_only=True)
class InstanceDTO:
    id: str
    token_hash: str
    slicer_version: str | None = None
    printer: JsonObject = field(default_factory=dict)
    modes: tuple[str, ...] = ()
    scene_epoch: str = ""
    scene_version: int = 0
    state: JsonObject = field(default_factory=dict)
    contract_version: str | None = None
    last_seen_at: datetime | None = None
    active_conversation_id: str | None = None
