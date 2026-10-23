import asyncio
from dataclasses import replace

from app.domain.chat import ChatRequest, ChatResponse, LlmConnection, ToolDefinition
from app.domain.errors import DomainError, LlmNotConfigured
from app.domain.protocol import EVENT_ERROR
from app.domain.run import TERMINAL_STATES, WAITING_STATES, RunState
from app.domain.tools import load_catalog
from app.usecase.agent_completion import ArtifactCompletion
from app.usecase.agent_flow import Flow
from app.usecase.agent_tools import ToolHandler
from app.usecase.config import AgentConfig
from app.usecase.context import build_messages
from app.usecase.dto.run import RunDTO, TranscriptEntry
from app.usecase.dto.tools import ToolCallDTO
from app.usecase.events import EventPublisher
from app.usecase.interface import Logger
from app.usecase.interface.llm import ChatModel, LlmConnectionStore
from app.usecase.interface.runtime import CallSignals, Clock
from app.usecase.interface.storage import UnitOfWorkFactory
from app.usecase.prompts import HELP_PROMPT, SUMMARY_PROMPT, SYSTEM_PROMPT
from app.usecase.readiness import InstanceReadiness
from app.usecase.run_store import RunStore
from app.usecase.tool_executor import ToolExecutor
from app.usecase.tool_results import error_entry

TOOLS = tuple(
    ToolDefinition(name=tool.name, description=tool.description, parameters=tool.input_schema)
    for tool in load_catalog()
)


class AgentLoop:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        store: RunStore,
        chat_model: ChatModel,
        connections: LlmConnectionStore,
        handler: ToolHandler,
        executor: ToolExecutor,
        events: EventPublisher,
        signals: CallSignals,
        clock: Clock,
        config: AgentConfig,
        logger: Logger,
        readiness: InstanceReadiness,
    ) -> None:
        self._readiness = readiness
        self._uow_factory = uow_factory
        self._store = store
        self._chat_model = chat_model
        self._connections = connections
        self._handler = handler
        self._executor = executor
        self._events = events
        self._signals = signals
        self._clock = clock
        self._config = config
        self._logger = logger
        self._completion = ArtifactCompletion(
            uow_factory, store, clock, signals, config, self.finish_with_summary, self._fail
        )

    async def run(self, run_id: str) -> None:
        try:
            await self._drive(run_id)
        except asyncio.CancelledError:
            raise
        except DomainError as exc:
            await self._fail(run_id, exc.code, exc.message)
        except Exception as exc:  # noqa: BLE001 - task boundary must record the failure
            self._logger.error("agent_loop_crashed", exc=exc, run_id=run_id)
            await self._fail(run_id, "internal_error", "Internal error")

    async def _drive(self, run_id: str) -> None:
        while True:
            run = await self._store.load(run_id)
            if run is None or run.state in TERMINAL_STATES or run.state in WAITING_STATES:
                return
            if not self._readiness.ready(run.instance_id):
                return
            if run.steps >= self._config.max_steps:
                await self._fail(run_id, "step_limit", "The agent reached its step limit")
                return
            flow = await self._advance(run)
            if flow in {Flow.WAIT, Flow.SUSPEND}:
                return
            if flow is Flow.HELP:
                await self._ask_for_help(run_id)
                return

    async def _advance(self, run: RunDTO) -> Flow:
        if run.state is RunState.SAVING:
            return await self._completion.wait(run)
        pending = await self._unfinished(run)
        if pending is not None:
            finished = await self._executor.run_call(
                pending, run.instance_id, self._config.tool_timeout_s
            )
            return Flow.SUSPEND if finished is None else await self._handler.finish(run, finished)
        if await self._reconcile(run):
            return Flow.CONTINUE
        if run.state in {RunState.EXECUTING_TOOL, RunState.SLICING}:
            return await self._resume_batch(run)
        return await self._llm_step(run)

    async def _resume_batch(self, run: RunDTO) -> Flow:
        async with self._uow_factory() as uow:
            batch = await uow.batches.get_accepted_for_run(run.id)
        if batch is not None:
            return await self._handler.execute_batch(run, batch)
        await self._store.move(
            run.id,
            RunState.AGENT_WORKING if run.requirements_ready else RunState.INTERVIEWING,
            "nothing to execute",
        )
        return Flow.CONTINUE

    async def _unfinished(self, run: RunDTO) -> ToolCallDTO | None:
        async with self._uow_factory() as uow:
            calls = await uow.tool_calls.list_for_run(run.id)
        return next((call for call in calls if not call.status.finished), None)

    async def _reconcile(self, run: RunDTO) -> bool:
        async with self._uow_factory() as uow:
            transcript = await uow.runs.list_transcript(run.id)
            calls = await uow.tool_calls.list_for_run(run.id)
        answered = {entry.tool_call_id for entry in transcript if entry.role == "tool"}
        by_llm_id = {call.llm_call_id: call for call in calls}
        changed = False
        for entry in transcript:
            for item in entry.tool_calls:
                llm_id = str(item["id"])
                if llm_id in answered:
                    continue
                call = by_llm_id.get(llm_id)
                if call is not None and call.status.finished:
                    await self._handler.finish(run, call)
                elif call is None and not await self._is_waiting_batch(run, llm_id):
                    await self._store.append(
                        run.id,
                        error_entry(llm_id, "skipped", "Not executed: the run was interrupted."),
                    )
                else:
                    continue
                answered.add(llm_id)
                changed = True
        return changed

    async def _is_waiting_batch(self, run: RunDTO, llm_id: str) -> bool:
        async with self._uow_factory() as uow:
            question = await uow.runs.get_open_question_batch(run.id)
            proposed = await uow.batches.get_proposed_for_run(run.id)
            accepted = await uow.batches.get_accepted_for_run(run.id)
        return any(
            item is not None and item.call_id == llm_id for item in (question, proposed, accepted)
        )

    async def _llm_step(self, run: RunDTO) -> Flow:
        response = await self._complete(run, TOOLS)
        run = await self._store.save(run, lambda fresh: replace(fresh, steps=fresh.steps + 1))
        await self._store.append(
            run.id,
            TranscriptEntry(
                role="assistant",
                content=response.text,
                tool_calls=tuple(
                    {"id": call.id, "name": call.name, "arguments": call.arguments}
                    for call in response.tool_calls
                ),
            ),
        )
        if response.text:
            await self._store.say(run, response.text)
        if not response.tool_calls:
            await self._store.move(run.id, RunState.AWAITING_USER, "assistant replied")
            return Flow.WAIT
        return await self._handler.handle(run, response.tool_calls)

    async def _complete(
        self, run: RunDTO, tools: tuple[ToolDefinition, ...], prompt: str | None = None
    ) -> ChatResponse:
        connection = self._connection(run)
        async with self._uow_factory() as uow:
            instance = await uow.instances.get(run.instance_id)
            conversation = await uow.conversations.get(run.conversation_id)
            attachments = await uow.attachments.list_for_conversation(run.conversation_id)
            transcript = await uow.runs.list_transcript(run.id)
            assert instance is not None and conversation is not None
            messages = await build_messages(
                uow,
                SYSTEM_PROMPT + (f"\n{prompt}" if prompt else ""),
                run,
                transcript,
                instance,
                attachments,
                conversation.mode.value,
            )
        return await self._chat_model.chat(connection, ChatRequest(tuple(messages), tools))

    def _connection(self, run: RunDTO) -> LlmConnection:
        connection = self._connections.get(run.instance_id)
        if connection is None:
            raise LlmNotConfigured()
        return connection

    async def _ask_for_help(self, run_id: str) -> None:
        run = await self._store.load(run_id)
        if run is None:
            return
        response = await self._complete(run, (), HELP_PROMPT)
        await self._store.append(run_id, TranscriptEntry(role="assistant", content=response.text))
        await self._store.say(run, response.text)
        await self._store.move(run_id, RunState.AWAITING_USER, "help requested")

    async def finish_with_summary(self, run: RunDTO) -> None:
        await self._store.move(run.id, RunState.COMPLETED, "artifacts saved")
        try:
            response = await self._complete(run, (), SUMMARY_PROMPT)
        except DomainError as exc:
            self._logger.warning("summary_failed", code=exc.code, run_id=run.id)
            return
        await self._store.append(run.id, TranscriptEntry(role="assistant", content=response.text))
        await self._store.say(run, response.text)

    async def _fail(self, run_id: str, code: str, message: str) -> None:
        run = await self._store.load(run_id)
        if run is None or run.state in TERMINAL_STATES:
            return
        await self._store.save(run, lambda fresh: replace(fresh, last_error=f"{code}: {message}"))
        await self._store.move(run_id, RunState.FAILED, code)
        await self._events.emit(run, EVENT_ERROR, {"code": code, "message": message})
