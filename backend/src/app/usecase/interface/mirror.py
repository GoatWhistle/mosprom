from typing import Protocol

from app.domain.jsonvalue import JsonObject


class RequestMirror(Protocol):
    def submit(self, body: JsonObject) -> None: ...

    async def aclose(self) -> None: ...
