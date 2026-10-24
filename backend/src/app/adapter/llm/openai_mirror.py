import asyncio
import time

import httpx

from app.domain.jsonvalue import JsonObject
from app.usecase.interface import Logger


class OpenAiMirror:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_s: float,
        logger: Logger,
        drain_s: float = 5.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/") + "/",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout_s,
            transport=transport,
        )
        self._model = model
        self._logger = logger
        self._drain_s = drain_s
        self._tasks: set[asyncio.Task[None]] = set()

    def submit(self, body: JsonObject) -> None:
        task = asyncio.create_task(self._send({**body, "model": self._model, "stream": False}))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def aclose(self) -> None:
        if self._tasks:
            _, pending = await asyncio.wait(set(self._tasks), timeout=self._drain_s)
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
        await self._client.aclose()

    async def _send(self, body: JsonObject) -> None:
        started = time.monotonic()
        try:
            response = await self._client.post("chat/completions", json=body)
        except httpx.HTTPError as exc:
            self._logger.warning("mirror_failed", model=self._model, error=type(exc).__name__)
            return
        self._logger.info(
            "mirror_sent",
            model=self._model,
            status=response.status_code,
            elapsed_ms=round((time.monotonic() - started) * 1000),
        )


class DisabledMirror:
    def submit(self, body: JsonObject) -> None:
        return None

    async def aclose(self) -> None:
        return None
