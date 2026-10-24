import asyncio
import json

import httpx
import pytest

from app.adapter.llm.openai_mirror import OpenAiMirror
from app.domain.jsonvalue import JsonObject
from app.usecase.interface import LogValue


class RecordingLogger:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, LogValue]]] = []

    def info(self, event: str, **fields: LogValue) -> None:
        self.events.append((event, fields))

    def warning(self, event: str, **fields: LogValue) -> None:
        self.events.append((event, fields))

    def error(self, event: str, *, exc: BaseException | None = None, **fields: LogValue) -> None:
        self.events.append((event, fields))


def _mirror(
    handler: httpx.MockTransport, logger: RecordingLogger, drain_s: float = 5.0
) -> OpenAiMirror:
    return OpenAiMirror("https://llm.example/v1/", "secret", "qwen", 10.0, logger, drain_s, handler)


async def test_sends_body_with_mirror_model() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"choices": []})

    logger = RecordingLogger()
    mirror = _mirror(httpx.MockTransport(handle), logger)
    body: JsonObject = {"model": "opus", "messages": [{"role": "user", "content": "hi"}]}
    mirror.submit(body)
    await mirror.aclose()

    [request] = requests
    assert str(request.url) == "https://llm.example/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer secret"
    assert json.loads(request.content) == {**body, "model": "qwen", "stream": False}
    assert body["model"] == "opus"
    assert [(event, fields["status"]) for event, fields in logger.events] == [("mirror_sent", 200)]


@pytest.mark.parametrize(
    "error", [httpx.ConnectError("down"), httpx.ReadTimeout("slow"), RuntimeError("bug")]
)
async def test_any_failure_is_logged_not_raised(error: Exception) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        raise error

    logger = RecordingLogger()
    mirror = _mirror(httpx.MockTransport(handle), logger)
    mirror.submit({"messages": []})
    await mirror.aclose()

    assert logger.events == [("mirror_failed", {"model": "qwen", "error": type(error).__name__})]
    assert "secret" not in repr(logger.events)


@pytest.mark.parametrize("status", [402, 429, 500, 503])
async def test_error_status_is_logged_as_rejected(status: int) -> None:
    logger = RecordingLogger()
    mirror = _mirror(httpx.MockTransport(lambda request: httpx.Response(status)), logger)
    mirror.submit({"messages": []})
    await mirror.aclose()

    assert [(event, fields["status"]) for event, fields in logger.events] == [
        ("mirror_rejected", status)
    ]


async def test_close_cancels_requests_after_drain() -> None:
    async def handle(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(10)
        return httpx.Response(200)

    logger = RecordingLogger()
    mirror = _mirror(httpx.MockTransport(handle), logger, drain_s=0.01)
    mirror.submit({"messages": []})
    await mirror.aclose()

    assert logger.events == []
