from dataclasses import replace

from app.domain.chat import ToolCall
from app.domain.jsonvalue import JsonObject
from app.domain.protocol import EVENT_QUESTION
from app.domain.run import RunState
from app.usecase.agent_flow import Flow
from app.usecase.dto.run import QuestionBatchDTO, RunDTO
from app.usecase.events import EventPublisher
from app.usecase.interface.runtime import Clock, IdGenerator
from app.usecase.interface.storage import UnitOfWorkFactory
from app.usecase.run_store import RunStore
from app.usecase.tool_results import error_entry


class QuestionHandler:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        store: RunStore,
        events: EventPublisher,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._uow_factory = uow_factory
        self._store = store
        self._events = events
        self._clock = clock
        self._ids = ids

    async def ask(self, run: RunDTO, tool_call: ToolCall, arguments: JsonObject) -> Flow:
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
