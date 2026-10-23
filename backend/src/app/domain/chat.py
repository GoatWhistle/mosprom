from dataclasses import dataclass, field
from enum import StrEnum

from app.domain.jsonvalue import JsonObject


class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True, slots=True)
class ImagePart:
    mime_type: str
    data: bytes


@dataclass(frozen=True, slots=True)
class ToolCall:
    id: str
    name: str
    arguments: JsonObject


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: Role
    text: str = ""
    images: tuple[ImagePart, ...] = ()
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    parameters: JsonObject


@dataclass(frozen=True, slots=True)
class ChatRequest:
    messages: tuple[ChatMessage, ...]
    tools: tuple[ToolDefinition, ...] = ()


@dataclass(frozen=True, slots=True)
class ChatResponse:
    text: str
    tool_calls: tuple[ToolCall, ...] = field(default_factory=tuple)
    finish_reason: str | None = None


@dataclass(frozen=True, slots=True)
class LlmConnection:
    base_url: str
    model: str
    api_key: str = field(repr=False)
