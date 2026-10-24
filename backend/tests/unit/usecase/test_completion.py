import asyncio

import pytest

from app.domain.chat import ChatRequest, ChatResponse, LlmConnection
from app.domain.errors import InvalidRequest
from app.domain.jsonvalue import JsonObject
from app.usecase.completion import CompletionService


class RecordingModel:
    def __init__(self) -> None:
        self.connections: list[LlmConnection] = []

    async def chat(self, connection: LlmConnection, request: ChatRequest) -> ChatResponse:
        self.connections.append(connection)
        return ChatResponse(text="ok")

    async def aclose(self) -> None:
        return None


class RecordingMirror:
    def __init__(self) -> None:
        self.bodies: list[JsonObject] = []

    def submit(self, body: JsonObject) -> None:
        self.bodies.append(body)

    async def aclose(self) -> None:
        return None


@pytest.mark.parametrize("requested", ["qwen", "sonnet", "claude-haiku-4-5", None])
def test_always_uses_opus(requested: str | None) -> None:
    model = RecordingModel()
    body: JsonObject = {"messages": [{"role": "user", "content": "hi"}]}
    if requested is not None:
        body["model"] = requested
    result = asyncio.run(CompletionService(model, RecordingMirror()).complete("token", body))
    assert [c.model for c in model.connections] == ["opus"]
    assert result["model"] == "opus"


def test_mirrors_valid_request_body() -> None:
    mirror = RecordingMirror()
    body: JsonObject = {"model": "x", "messages": [{"role": "user", "content": "hi"}]}
    result = asyncio.run(CompletionService(RecordingModel(), mirror).complete("token", body))
    assert mirror.bodies == [body]
    assert result["choices"] == [
        {"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}
    ]


def test_invalid_request_is_not_mirrored() -> None:
    mirror = RecordingMirror()
    with pytest.raises(InvalidRequest):
        asyncio.run(CompletionService(RecordingModel(), mirror).complete("token", {"messages": []}))
    assert mirror.bodies == []
