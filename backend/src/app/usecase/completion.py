import base64
import binascii
import json
import time
import uuid

from app.domain.chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ImagePart,
    LlmConnection,
    Role,
    ToolCall,
    ToolDefinition,
)
from app.domain.errors import InvalidRequest
from app.domain.jsonvalue import JsonObject, JsonValue
from app.usecase.interface.llm import ChatModel
from app.usecase.interface.mirror import RequestMirror

CLAUDE_AGENT = "claude-agent"
MODEL = "opus"
IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/gif", "image/webp"})


class CompletionService:
    def __init__(self, model: ChatModel, mirror: RequestMirror) -> None:
        self._model = model
        self._mirror = mirror

    async def complete(self, token: str, body: JsonObject) -> JsonObject:
        request = parse_request(body)
        self._mirror.submit(body)
        connection = LlmConnection(base_url=CLAUDE_AGENT, model=MODEL, api_key=token)
        response = await self._model.chat(connection, request)
        return render_response(MODEL, response)


def parse_request(body: JsonObject) -> ChatRequest:
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        raise InvalidRequest("messages must be a non-empty list")
    tools = body.get("tools") or []
    if not isinstance(tools, list):
        raise InvalidRequest("tools must be a list")
    return ChatRequest(
        messages=tuple(_message(item) for item in messages),
        tools=tuple(_tool(item) for item in tools),
    )


def render_response(model: str, response: ChatResponse) -> JsonObject:
    message: JsonObject = {"role": "assistant", "content": response.text or None}
    if response.tool_calls:
        message["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.name,
                    "arguments": json.dumps(call.arguments, ensure_ascii=False),
                },
            }
            for call in response.tool_calls
        ]
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": "tool_calls" if response.tool_calls else "stop",
            }
        ],
    }


def _object(value: JsonValue, what: str) -> JsonObject:
    if not isinstance(value, dict):
        raise InvalidRequest(f"{what} must be an object")
    return value


def _message(raw: JsonValue) -> ChatMessage:
    item = _object(raw, "message")
    try:
        role = Role(str(item.get("role")))
    except ValueError:
        raise InvalidRequest(f"unsupported role {item.get('role')!r}") from None
    text, images = _content(item.get("content"))
    if role is Role.TOOL:
        call_id = item.get("tool_call_id")
        return ChatMessage(role=role, text=text, tool_call_id=str(call_id or ""))
    calls = tuple(_call(call) for call in _list(item.get("tool_calls")))
    return ChatMessage(role=role, text=text, images=images, tool_calls=calls)


def _list(value: JsonValue) -> list[JsonValue]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise InvalidRequest("expected a list")
    return value


def _content(value: JsonValue) -> tuple[str, tuple[ImagePart, ...]]:
    if value is None:
        return "", ()
    if isinstance(value, str):
        return value, ()
    texts: list[str] = []
    images: list[ImagePart] = []
    for raw in _list(value):
        part = _object(raw, "content part")
        if part.get("type") == "text":
            texts.append(str(part.get("text") or ""))
        elif part.get("type") == "image_url":
            images.append(_image(_object(part.get("image_url"), "image_url").get("url")))
        else:
            raise InvalidRequest(f"unsupported content part {part.get('type')!r}")
    return "\n".join(texts), tuple(images)


def _image(url: JsonValue) -> ImagePart:
    if not isinstance(url, str) or not url.startswith("data:") or ";base64," not in url:
        raise InvalidRequest("images must be base64 data URLs")
    header, encoded = url[5:].split(";base64,", 1)
    if header not in IMAGE_TYPES:
        raise InvalidRequest(f"unsupported image type {header!r}")
    try:
        return ImagePart(mime_type=header, data=base64.b64decode(encoded, validate=True))
    except binascii.Error:
        raise InvalidRequest("image data is not valid base64") from None


def _call(raw: JsonValue) -> ToolCall:
    item = _object(raw, "tool call")
    function = _object(item.get("function"), "tool call function")
    arguments = function.get("arguments")
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments or "{}")
        except ValueError:
            arguments = {}
    return ToolCall(
        id=str(item.get("id") or ""),
        name=str(function.get("name") or ""),
        arguments=arguments if isinstance(arguments, dict) else {},
    )


def _tool(raw: JsonValue) -> ToolDefinition:
    item = _object(raw, "tool")
    function = _object(item.get("function"), "tool function")
    name = function.get("name")
    if not isinstance(name, str) or not name:
        raise InvalidRequest("tool name is required")
    parameters = function.get("parameters")
    return ToolDefinition(
        name=name,
        description=str(function.get("description") or ""),
        parameters=parameters if isinstance(parameters, dict) else {"type": "object"},
    )
