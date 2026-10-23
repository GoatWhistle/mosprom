import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.adapter.llm.openai_compatible import OpenAICompatibleChatAdapter
from app.adapter.log.stdlib import StdlibLogger
from app.adapter.runtime.connections import InMemoryLlmConnectionStore
from app.adapter.runtime.gateway import InstanceGateway
from app.adapter.runtime.scheduler import AsyncioRunScheduler
from app.adapter.runtime.signals import AsyncCallSignals
from app.adapter.runtime.system import SystemClock, UuidGenerator
from app.controller.errors import ErrorHandlers
from app.controller.router import api_router_v1
from app.controller.services import Services
from app.repository.postgres.pool import PostgresUnitOfWorkFactory, open_pool
from app.settings import Settings, load_settings
from app.usecase.agent import AgentLoop
from app.usecase.agent_tools import ToolHandler
from app.usecase.artifacts import ArtifactService
from app.usecase.conversations import ConversationService
from app.usecase.events import EventPublisher
from app.usecase.instances import InstanceService
from app.usecase.plugin_session import PluginSession
from app.usecase.readiness import InstanceReadiness
from app.usecase.run_store import RunStore
from app.usecase.runs import RunService
from app.usecase.tool_executor import ToolExecutor


def create_app(
    settings: Settings | None = None, transport: httpx.AsyncBaseTransport | None = None
) -> FastAPI:
    config = settings or load_settings(os.environ)
    logger = StdlibLogger("app")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        pool = await open_pool(config.database_url, config.pool_max_size)
        client = httpx.AsyncClient(timeout=config.llm_timeout_s, transport=transport)
        chat_model = OpenAICompatibleChatAdapter(client)
        uow_factory = PostgresUnitOfWorkFactory(pool)
        clock, ids = SystemClock(), UuidGenerator()
        gateway, signals = InstanceGateway(), AsyncCallSignals()
        connections = InMemoryLlmConnectionStore()
        readiness = InstanceReadiness()
        events = EventPublisher(uow_factory, gateway, clock, ids)
        store = RunStore(uow_factory, clock, ids, events)
        executor = ToolExecutor(uow_factory, gateway, signals, clock, ids)
        handler = ToolHandler(uow_factory, store, executor, events, clock, ids, config.agent)
        agent = AgentLoop(
            uow_factory,
            store,
            chat_model,
            connections,
            handler,
            executor,
            events,
            signals,
            clock,
            config.agent,
            logger,
            readiness,
        )
        scheduler = AsyncioRunScheduler(agent.run)
        runs = RunService(uow_factory, scheduler, gateway, clock, ids)
        instances = InstanceService(uow_factory, connections, signals, clock, ids)
        app.state.services = Services(
            instances=instances,
            conversations=ConversationService(uow_factory, clock, ids, config.agent),
            runs=runs,
            artifacts=ArtifactService(uow_factory, signals, clock, ids, config.agent),
            session=PluginSession(readiness, instances, runs, uow_factory, clock, ids),
            registry=gateway,
        )
        try:
            yield
        finally:
            await scheduler.aclose()
            await chat_model.aclose()
            await pool.close()

    app = FastAPI(title="brim", lifespan=lifespan)
    ErrorHandlers(logger).register(app)
    app.include_router(api_router_v1)
    return app
