from app.domain.chat import ChatRequest, ChatResponse, LlmConnection
from app.domain.errors import ModelFailure


class UnavailableChatModel:
    def __init__(self, reason: str) -> None:
        self._reason = reason

    async def chat(self, connection: LlmConnection, request: ChatRequest) -> ChatResponse:
        raise ModelFailure(self._reason)

    async def aclose(self) -> None:
        return None
