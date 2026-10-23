from collections.abc import Callable
from dataclasses import replace

from app.domain.protocol import EVENT_ASSISTANT_MESSAGE, EVENT_RUN_STATE
from app.domain.run import TRANSITIONS, RunState
from app.usecase.dto.conversation import MessageDTO
from app.usecase.dto.run import RunDTO, TranscriptEntry
from app.usecase.events import EventPublisher
from app.usecase.interface.runtime import Clock, IdGenerator
from app.usecase.interface.storage import UnitOfWorkFactory


class RunStore:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        clock: Clock,
        ids: IdGenerator,
        events: EventPublisher,
    ) -> None:
        self._uow_factory = uow_factory
        self._events = events
        self._clock = clock
        self._ids = ids

    async def load(self, run_id: str) -> RunDTO | None:
        async with self._uow_factory() as uow:
            return await uow.runs.get(run_id)

    async def project_version(self, conversation_id: str) -> int:
        async with self._uow_factory() as uow:
            conversation = await uow.conversations.get(conversation_id)
        return conversation.project_version if conversation is not None else 0

    async def move(self, run_id: str, target: RunState, reason: str) -> bool:
        async with self._uow_factory() as uow:
            run = await uow.runs.get(run_id, lock=True)
            if run is None:
                return False
            if run.state is target:
                return True
            if target not in TRANSITIONS[run.state]:
                return False
            moved = await uow.runs.transition(run_id, run.state, target, reason, self._clock.now())
            await uow.commit()
        if moved:
            await self._events.emit(
                replace(run, state=target),
                EVENT_RUN_STATE,
                {"state": target.value, "reason": reason},
            )
        return moved

    async def save(self, run: RunDTO, change: Callable[[RunDTO], RunDTO]) -> RunDTO:
        async with self._uow_factory() as uow:
            fresh = await uow.runs.get(run.id, lock=True)
            assert fresh is not None
            updated = change(fresh)
            updated = replace(updated, updated_at=self._clock.now())
            await uow.runs.update(updated)
            await uow.commit()
        return updated

    async def append(self, run_id: str, entry: TranscriptEntry) -> None:
        async with self._uow_factory() as uow:
            await uow.runs.add_transcript(run_id, entry)
            await uow.commit()

    async def say(self, run: RunDTO, text: str) -> None:
        async with self._uow_factory() as uow:
            await uow.conversations.add_message(
                MessageDTO(
                    id=self._ids.new_id(),
                    conversation_id=run.conversation_id,
                    run_id=run.id,
                    role="assistant",
                    content=text,
                    attachment_ids=(),
                    created_at=self._clock.now(),
                )
            )
            await uow.conversations.touch(run.conversation_id, self._clock.now())
            await uow.commit()
        await self._events.emit(run, EVENT_ASSISTANT_MESSAGE, {"text": text})
