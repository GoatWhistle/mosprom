from collections.abc import Mapping

from app.domain.chat import ChatRequest, ChatResponse, LlmConnection
from app.domain.errors import ModelFailure
from app.usecase.interface.llm import ChatModel


class ChatModelRouter:
    def __init__(self, default: ChatModel, routes: Mapping[str, ChatModel]) -> None:
        self._default = default
        self._routes = dict(routes)

    async def chat(self, connection: LlmConnection, request: ChatRequest) -> ChatResponse:
        return await self._pick(connection).chat(connection, request)

    async def aclose(self) -> None:
        for model in (self._default, *self._routes.values()):
            await model.aclose()

    def _pick(self, connection: LlmConnection) -> ChatModel:
        scheme = connection.base_url.strip().lower().split("://", 1)[0]
        return self._routes.get(scheme, self._default)


class UnavailableChatModel:
    def __init__(self, reason: str) -> None:
        self._reason = reason

    async def chat(self, connection: LlmConnection, request: ChatRequest) -> ChatResponse:
        raise ModelFailure(self._reason)

    async def aclose(self) -> None:
        return None
