from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.usecase.dto.conversation import AttachmentDTO, ConversationDTO, MessageDTO


class ConversationResponse(BaseModel):
    id: str
    title: str
    mode: Literal["auto", "ask"]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def of(cls, item: ConversationDTO) -> "ConversationResponse":
        return cls(
            id=item.id,
            title=item.title,
            mode=item.mode.value,
            created_at=item.created_at,
            updated_at=item.updated_at,
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
