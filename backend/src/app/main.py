import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.adapter.llm.unavailable import UnavailableChatModel
from app.adapter.log.stdlib import StdlibLogger
from app.controller.errors import ErrorHandlers
from app.controller.openai.router import router as openai_router
from app.controller.router import api_router_v1
from app.settings import Settings, load_settings
from app.usecase.completion import CompletionService
from app.usecase.interface.llm import ChatModel


def create_app(settings: Settings | None = None, model: ChatModel | None = None) -> FastAPI:
    config = settings or load_settings(os.environ)
    logger = StdlibLogger("app")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        chat_model = model or build_claude_agent(config.llm_timeout_s)
        app.state.completions = CompletionService(chat_model)
        try:
            yield
        finally:
            await chat_model.aclose()

    app = FastAPI(title="brim", lifespan=lifespan)
    ErrorHandlers(logger).register(app)
    app.include_router(api_router_v1)
    app.include_router(openai_router)
    return app


def build_claude_agent(timeout_s: float) -> ChatModel:
    try:
        from app.adapter.llm.claude_agent import ClaudeAgentChatAdapter
    except ImportError:
        return UnavailableChatModel(
            "claude-agent-sdk is not installed; build the backend image with LLM=true"
        )
    return ClaudeAgentChatAdapter(timeout_s)
