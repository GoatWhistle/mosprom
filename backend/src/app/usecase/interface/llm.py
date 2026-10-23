from typing import Protocol

from app.domain.chat import ChatRequest, ChatResponse, LlmConnection


class ChatModel(Protocol):
    async def chat(self, connection: LlmConnection, request: ChatRequest) -> ChatResponse: ...

    async def aclose(self) -> None: ...
