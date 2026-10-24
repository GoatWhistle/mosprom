import asyncio
import time

import httpx
from fastapi.testclient import TestClient

from app.adapter.llm.openai_mirror import OpenAiMirror
from app.domain.chat import ChatRequest, ChatResponse, LlmConnection
from app.main import create_app
from app.settings import Settings
from app.usecase.interface import Logger, RequestMirror


class FixedModel:
    async def chat(self, connection: LlmConnection, request: ChatRequest) -> ChatResponse:
        return ChatResponse(text="claude")

    async def aclose(self) -> None:
        return None


async def _hang(request: httpx.Request) -> httpx.Response:
    await asyncio.sleep(30)
    return httpx.Response(200)


def _down(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("down", request=request)


def _ask(handler: httpx.MockTransport) -> tuple[int, object, float]:
    def build(config: Settings, logger: Logger) -> RequestMirror:
        return OpenAiMirror("https://llm.example/v1", "k", "qwen", 60.0, logger, 0.01, handler)

    app = create_app(Settings(), FixedModel(), build)
    started = time.monotonic()
    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer t"},
            json={"messages": [{"role": "user", "content": "hi"}]},
        )
        elapsed = time.monotonic() - started
    return response.status_code, response.json()["choices"][0]["message"]["content"], elapsed


def test_claude_answers_when_qwen_hangs() -> None:
    status, content, elapsed = _ask(httpx.MockTransport(_hang))
    assert (status, content) == (200, "claude")
    assert elapsed < 5


def test_claude_answers_when_qwen_is_down() -> None:
    status, content, _ = _ask(httpx.MockTransport(_down))
    assert (status, content) == (200, "claude")
