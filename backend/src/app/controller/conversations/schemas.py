from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.jsonvalue import JsonObject
from app.usecase.dto.conversation import AttachmentDTO, ConversationDTO, MessageDTO


class ProjectResponse(BaseModel):
    state: str
    version: int
    sha256: str | None
    saved_at: datetime | None


class ProjectRequest(BaseModel):
    state: Literal["saved", "empty"]
    sha256: str | None = Field(default=None, min_length=64, max_length=64)
    active: bool = True


class ConversationResponse(BaseModel):
    id: str
    title: str
    mode: Literal["auto", "ask"]
    created_at: datetime
    updated_at: datetime
    project: "ProjectResponse"

    @classmethod
    def of(cls, item: ConversationDTO) -> "ConversationResponse":
        return cls(
            id=item.id,
            title=item.title,
            mode=item.mode.value,
            created_at=item.created_at,
            updated_at=item.updated_at,
            project=ProjectResponse(
                state=item.project_state,
                version=item.project_version,
                sha256=item.project_sha256,
                saved_at=item.project_saved_at,
            ),
        )


class MessageResponse(BaseModel):
    id: str
    run_id: str | None
    role: str
    content: str
    attachment_ids: list[str]
    created_at: datetime

    @classmethod
    def of(cls, item: MessageDTO) -> "MessageResponse":
        return cls(
            id=item.id,
            run_id=item.run_id,
            role=item.role,
            content=item.content,
            attachment_ids=list(item.attachment_ids),
            created_at=item.created_at,
        )


class ConversationDetail(BaseModel):
    conversation: ConversationResponse
    messages: list[MessageResponse]
    runtime: JsonObject


class ConversationPageResponse(BaseModel):
    items: list[ConversationResponse]
    next_cursor: str | None


class CreateConversationRequest(BaseModel):
    title: str = ""
    mode: Literal["auto", "ask"] = "ask"


class SendMessageRequest(BaseModel):
    text: str = ""
    attachment_ids: list[str] = []
    mode: Literal["auto", "ask"] | None = None
    client_message_id: str | None = Field(default=None, min_length=1, max_length=64)


class SendMessageResponse(BaseModel):
    run_id: str
    message_id: str


class ModeRequest(BaseModel):
    mode: Literal["auto", "ask"]


class AttachmentResponse(BaseModel):
    id: str
    name: str
    content_type: str
    size: int
    sha256: str

    @classmethod
    def of(cls, item: AttachmentDTO) -> "AttachmentResponse":
        return cls(
            id=item.id,
            name=item.name,
            content_type=item.content_type,
            size=item.size,
            sha256=item.sha256,
        )
