from dataclasses import dataclass
from datetime import datetime

from app.domain.confirmation import Mode


@dataclass(frozen=True, slots=True, kw_only=True)
class ConversationDTO:
    id: str
    instance_id: str
    title: str
    mode: Mode
    created_at: datetime
    updated_at: datetime
    project_state: str = "none"
    project_version: int = 0
    project_sha256: str | None = None
    project_saved_at: datetime | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class MessageDTO:
    id: str
    conversation_id: str
    run_id: str | None
    role: str
    content: str
    attachment_ids: tuple[str, ...]
    created_at: datetime
    client_message_id: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentDTO:
    id: str
    instance_id: str
    conversation_id: str | None
    source: str
    name: str
    content_type: str
    size: int
    sha256: str
    created_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class AttachmentBlob:
    meta: AttachmentDTO
    data: bytes


@dataclass(frozen=True, slots=True, kw_only=True)
class ConversationPage:
    items: tuple[ConversationDTO, ...]
    next_cursor: str | None
