from dataclasses import replace
from enum import StrEnum

from app.domain.chat import ToolCall
from app.domain.confirmation import BatchStatus, Mode, batch_hash, permits_execution
from app.domain.corrections import CorrectionState, limit_reached, operation_key, register_outcome
from app.domain.errors import InvalidRequest
from app.domain.jsonvalue import JsonObject
from app.domain.operations import operations_of, validate_tool_arguments
from app.domain.protocol import (
    EVENT_CONFIRMATION,
    EVENT_QUESTION,
    EVENT_TOOL_FINISHED,
    EVENT_TOOL_STARTED,
    STALE_SCENE,
)
from app.domain.run import RunState
from app.domain.tools import INTERVIEW_BLOCKED_TOOLS
from app.usecase.config import AgentConfig
from app.usecase.dto.run import QuestionBatchDTO, RunDTO
from app.usecase.dto.tools import CallStatus, ChangeBatchDTO, ToolCallDTO
from app.usecase.events import EventPublisher
from app.usecase.interface.runtime import Clock, IdGenerator
from app.usecase.interface.storage import UnitOfWorkFactory
from app.usecase.run_store import RunStore
from app.usecase.tool_executor import ToolExecutor
from app.usecase.tool_results import call_ok, error_code, error_entry, result_entry


class Flow(StrEnum):
    CONTINUE = "continue"
    WAIT = "wait"
    SUSPEND = "suspend"
    HELP = "help"


class ToolHandler:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        store: RunStore,
        executor: ToolExecutor,
        events: EventPublisher,
        clock: Clock,
        ids: IdGenerator,
        config: AgentConfig,
    ) -> None:
        self._uow_factory = uow_factory
        self._store = store
        self._executor = executor
        self._events = events
        self._clock = clock
        self._ids = ids
        self._config = config

    async def handle(self, run: RunDTO, calls: tuple[ToolCall, ...]) -> Flow:
        for index, tool_call in enumerate(calls):
            current = await self._store.load(run.id)
            if current is None:
                return Flow.SUSPEND
            flow = await self._one(current, tool_call)
            if flow is not Flow.CONTINUE:
                for skipped in calls[index + 1 :]:
                    await self._store.append(
                        run.id,
                        error_entry(skipped.id, "skipped", "Not executed: the run is waiting."),
                    )
                return flow
        return Flow.CONTINUE

    async def _one(self, run: RunDTO, tool_call: ToolCall) -> Flow:
        try:
            arguments = validate_tool_arguments(tool_call.name, tool_call.arguments)
        except InvalidRequest as exc:
            await self._store.append(
                run.id, error_entry(tool_call.id, "invalid_arguments", exc.message)
            )
            return Flow.CONTINUE
        if tool_call.name == "ask_user":
            return await self._ask(run, tool_call, arguments)
        if tool_call.name in INTERVIEW_BLOCKED_TOOLS and not run.requirements_ready:
            await self._store.append(
                run.id,
                error_entry(
                    tool_call.id,
                    "requirements_not_ready",
                    "Finish the interview with ask_user and a requirements_summary first.",
                ),
            )
            return Flow.CONTINUE
        if tool_call.name == "apply_changes":
            return await self._apply(run, tool_call, arguments)
        target = RunState.SLICING if tool_call.name == "slice" else RunState.EXECUTING_TOOL
        scene = await self._scene_version(run)
        call = await self._executor.create(
            run, tool_call.id, tool_call.name, arguments, scene, None
        )
        return await self.execute(run, call, target)

    async def _ask(self, run: RunDTO, tool_call: ToolCall, arguments: JsonObject) -> Flow:
        raw = arguments.get("questions")
        questions = (
            tuple(str(item["text"]) for item in raw if isinstance(item, dict) and "text" in item)
            if isinstance(raw, list)
            else ()
        )
        if not questions:
            summary = arguments.get("requirements_summary")
            if not isinstance(summary, str) or not summary.strip():
                await self._store.append(
                    run.id,
                    error_entry(
                        tool_call.id, "invalid_arguments", "requirements_summary is required"
                    ),
                )
                return Flow.CONTINUE
            updated = await self._store.save(
                run,
                lambda fresh: replace(fresh, requirements_ready=True, requirements_summary=summary),
            )
            await self._store.append(
                run.id, error_entry(tool_call.id, "ok", "Requirements accepted.")
            )
            await self._store.move(updated.id, RunState.AGENT_WORKING, "requirements ready")
            return Flow.CONTINUE
        batch = QuestionBatchDTO(
            id=self._ids.new_id(),
            run_id=run.id,
            call_id=tool_call.id,
            questions=questions,
            answer=None,
            created_at=self._clock.now(),
        )
        async with self._uow_factory() as uow:
            await uow.runs.add_question_batch(batch)
            await uow.commit()
        await self._store.move(run.id, RunState.AWAITING_USER, "ask_user")
        await self._events.emit(
            run, EVENT_QUESTION, {"batch_id": batch.id, "questions": list(questions)}
        )
        return Flow.WAIT

    async def _apply(self, run: RunDTO, tool_call: ToolCall, arguments: JsonObject) -> Flow:
        operations = operations_of(arguments)
        explanation = arguments.get("explanation")
        async with self._uow_factory() as uow:
            conversation = await uow.conversations.get(run.conversation_id)
            instance = await uow.instances.get(run.instance_id)
        assert conversation is not None and instance is not None
        auto = conversation.mode is Mode.AUTO
        batch = ChangeBatchDTO(
            id=self._ids.new_id(),
            run_id=run.id,
            call_id=tool_call.id,
            content_hash=batch_hash(operations),
            scene_version=instance.scene_version,
            operations=tuple(operations),
            explanation=explanation if isinstance(explanation, str) else "",
            status=BatchStatus.ACCEPTED if auto else BatchStatus.PROPOSED,
            created_at=self._clock.now(),
        )
        async with self._uow_factory() as uow:
            await uow.batches.add(batch)
            await uow.commit()
        if not auto:
            await self._store.move(run.id, RunState.AWAITING_CONFIRMATION, "confirmation needed")
            await self._events.emit(
                run,
                EVENT_CONFIRMATION,
                {
                    "batch_id": batch.id,
                    "operations": list(batch.operations),
                    "explanation": batch.explanation,
                    "scene_version": batch.scene_version,
                },
            )
            return Flow.WAIT
        return await self.execute_batch(run, batch)

    async def execute_batch(self, run: RunDTO, batch: ChangeBatchDTO) -> Flow:
        async with self._uow_factory() as uow:
            conversation = await uow.conversations.get(run.conversation_id)
            instance = await uow.instances.get(run.instance_id)
        assert conversation is not None and instance is not None
        allowed = permits_execution(
            mode=conversation.mode,
            operations=list(batch.operations),
            scene_version=instance.scene_version,
            batch_status=batch.status,
            batch_hash_value=batch.content_hash,
            batch_scene_version=batch.scene_version,
        )
        if not allowed:
            async with self._uow_factory() as uow:
                await uow.batches.set_status(
                    batch.id, batch.status, BatchStatus.STALE, None, self._clock.now()
                )
                await uow.commit()
            await self._store.append(
                run.id,
                error_entry(
                    batch.call_id, STALE_SCENE, "The scene changed; review the context and retry."
                ),
            )
            await self._store.move(run.id, _resume(run), "stale batch")
            return Flow.CONTINUE
        arguments: JsonObject = {
            "operations": list(batch.operations),
            "explanation": batch.explanation,
        }
        call = await self._executor.create(
            run, batch.call_id, "apply_changes", arguments, batch.scene_version, batch.id
        )
        return await self.execute(run, call, RunState.EXECUTING_TOOL)

    async def execute(self, run: RunDTO, call: ToolCallDTO, target: RunState) -> Flow:
        await self._store.move(run.id, target, f"run {call.tool}")
        await self._events.emit(
            run, EVENT_TOOL_STARTED, {"tool": call.tool, "call_id": call.call_id}
        )
        timeout = (
            self._config.slice_timeout_s if call.tool == "slice" else self._config.tool_timeout_s
        )
        finished = await self._executor.run_call(call, run.instance_id, timeout)
        if finished is None:
            return Flow.SUSPEND
        return await self.finish(run, finished)

    async def finish(self, run: RunDTO, call: ToolCallDTO) -> Flow:
        current = await self._store.load(run.id)
        assert current is not None
        await self._store.append(run.id, result_entry(call))
        await self._events.emit(
            current,
            EVENT_TOOL_FINISHED,
            {
                "tool": call.tool,
                "call_id": call.call_id,
                "ok": call_ok(call),
                "error": error_code(call),
            },
        )
        if call.batch_id is not None:
            async with self._uow_factory() as uow:
                await uow.batches.set_status(
                    call.batch_id,
                    BatchStatus.ACCEPTED,
                    BatchStatus.EXECUTED,
                    None,
                    self._clock.now(),
                )
                await uow.commit()
        if call.tool == "slice":
            await self._after_slice(current, call)
        else:
            await self._store.move(current.id, _resume(current), f"{call.tool} finished")
        return await self._corrections(current, call)

    async def _after_slice(self, run: RunDTO, call: ToolCallDTO) -> None:
        if call.scene_version is not None:
            async with self._uow_factory() as uow:
                await uow.tool_calls.save_slice_job(
                    run.id,
                    call.call_id,
                    call.scene_version,
                    "ok" if call_ok(call) else "failed",
                    call.result or {},
                    self._clock.now(),
                )
                await uow.commit()
        target = RunState.SAVING if call_ok(call) else _resume(run)
        await self._store.move(run.id, target, "slice finished")

    async def _scene_version(self, run: RunDTO) -> int:
        async with self._uow_factory() as uow:
            instance = await uow.instances.get(run.instance_id)
        assert instance is not None
        return instance.scene_version

    async def _corrections(self, run: RunDTO, call: ToolCallDTO) -> Flow:
        if call.tool not in {"apply_changes", "slice"} or error_code(call) in {STALE_SCENE}:
            return Flow.CONTINUE
        key = operation_key(call.tool, call.arguments, len(call.applied))
        state = register_outcome(
            CorrectionState(run.correction_key, run.correction_failures),
            key,
            succeeded=call_ok(call),
        )
        limit = limit_reached(state, self._config.correction_limit)
        await self._store.save(
            run,
            lambda fresh: replace(
                fresh,
                correction_key=state.key,
                correction_failures=state.failures,
                help_required=limit,
            ),
        )
        return Flow.HELP if limit and call.status is not CallStatus.COMPLETED else Flow.CONTINUE


def _resume(run: RunDTO) -> RunState:
    return RunState.AGENT_WORKING if run.requirements_ready else RunState.INTERVIEWING
