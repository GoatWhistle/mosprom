import asyncio

import pytest

from app.domain.chat import ChatRequest, ChatResponse, LlmConnection
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


@pytest.mark.parametrize("requested", ["qwen", "sonnet", "claude-haiku-4-5", None])
def test_always_uses_opus(requested: str | None) -> None:
    model = RecordingModel()
    body: JsonObject = {"messages": [{"role": "user", "content": "hi"}]}
    if requested is not None:
        body["model"] = requested
    result = asyncio.run(CompletionService(model).complete("token", body))
    assert [c.model for c in model.connections] == ["opus"]
    assert result["model"] == "opus"
