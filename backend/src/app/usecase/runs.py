from dataclasses import dataclass
from datetime import datetime

from app.domain.confirmation import BatchStatus, Decision, Mode
from app.domain.errors import (
    InvalidRequest,
    NoPendingBatch,
    NotFound,
    RunActive,
    RunFinished,
    RunNotWaiting,
)
from app.domain.protocol import CANCEL_RUN, STALE_SCENE
from app.domain.run import ACTIVE_STATES, TERMINAL_STATES, RunState, resume_state
from app.usecase.dto.conversation import MessageDTO
from app.usecase.dto.run import RunDTO, TranscriptEntry
from app.usecase.interface.runtime import Clock, IdGenerator, PluginGateway, RunScheduler
from app.usecase.interface.storage import UnitOfWork, UnitOfWorkFactory
from app.usecase.tool_results import error_entry


@dataclass(frozen=True, slots=True)
class MessageAccepted:
    run: RunDTO
    message: MessageDTO


class RunService:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        scheduler: RunScheduler,
        gateway: PluginGateway,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._uow_factory = uow_factory
        self._scheduler = scheduler
        self._gateway = gateway
        self._clock = clock
        self._ids = ids

    async def post_message(
        self,
        instance_id: str,
        conversation_id: str,
        text: str,
        attachment_ids: tuple[str, ...],
        mode: Mode | None,
    ) -> MessageAccepted:
        if not text.strip() and not attachment_ids:
            raise InvalidRequest("Message needs text or attachments")
        now = self._clock.now()
        async with self._uow_factory() as uow:
            conversation = await uow.conversations.get(conversation_id)
            if conversation is None or conversation.instance_id != instance_id:
                raise NotFound()
            if mode is not None and mode is not conversation.mode:
                await uow.conversations.set_mode(conversation_id, mode, now)
            for attachment_id in attachment_ids:
                blob = await uow.attachments.get_blob(attachment_id)
                if blob is None or blob.meta.instance_id != instance_id:
                    raise NotFound("Unknown attachment")
            await uow.attachments.link(attachment_ids, conversation_id)
            run = await uow.runs.get_active_for_instance(instance_id)
            if run is not None and run.conversation_id != conversation_id:
                raise RunActive()
            if run is not None and run.state is not RunState.AWAITING_USER:
                raise RunActive("The run is busy; wait for it or stop it first")
            answered = False
            if run is None:
                run = await self._start_run(uow, conversation_id, instance_id, now)
            else:
                answered = await self._answer_open_question(uow, run, text, attachment_ids)
            message = MessageDTO(
                id=self._ids.new_id(),
                conversation_id=conversation_id,
                run_id=run.id,
                role="user",
                content=text,
                attachment_ids=attachment_ids,
                created_at=now,
            )
            await uow.conversations.add_message(message)
            await uow.conversations.touch(conversation_id, now)
            if not answered:
                await uow.runs.add_transcript(
                    run.id,
                    TranscriptEntry(role="user", content=text, attachment_ids=attachment_ids),
                )
            if run.state is RunState.AWAITING_USER:
                await uow.runs.transition(
                    run.id, run.state, resume_state(run.requirements_ready), "user replied", now
                )
            await uow.commit()
        self._scheduler.start(run.id)
        return MessageAccepted(run=run, message=message)

    async def confirm(
        self, instance_id: str, run_id: str, decision: Decision, text: str | None
    ) -> RunDTO:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            run = await self._owned_run(uow, instance_id, run_id, lock=True)
            if run.state is not RunState.AWAITING_CONFIRMATION:
                raise RunNotWaiting()
            batch = await uow.batches.get_proposed_for_run(run_id)
            if batch is None:
                raise NoPendingBatch()
            instance = await uow.instances.get(instance_id)
            assert instance is not None
            fresh = (instance.scene_epoch, instance.scene_version) == (
                batch.scene_epoch,
                batch.scene_version,
            )
            if decision is Decision.ACCEPT and fresh:
                await uow.batches.set_status(
                    batch.id, BatchStatus.PROPOSED, BatchStatus.ACCEPTED, text, now
                )
                target = RunState.EXECUTING_TOOL
            else:
                status, code, message = _refusal(decision, fresh, text)
                await uow.batches.set_status(batch.id, BatchStatus.PROPOSED, status, text, now)
                await uow.runs.add_transcript(run_id, error_entry(batch.call_id, code, message))
                target = RunState.AGENT_WORKING
            await uow.runs.transition(run_id, run.state, target, f"decision {decision.value}", now)
            await uow.commit()
        self._scheduler.start(run_id)
        return run

    async def stop(self, instance_id: str, run_id: str) -> RunDTO:
        now = self._clock.now()
        async with self._uow_factory() as uow:
            run = await self._owned_run(uow, instance_id, run_id, lock=True)
            if run.state in TERMINAL_STATES:
                raise RunFinished()
            await uow.runs.transition(run_id, run.state, RunState.ABORTED, "stopped by user", now)
            await uow.commit()
        self._scheduler.cancel(run_id)
        await self._gateway.send(
            instance_id, {"type": CANCEL_RUN, "id": self._ids.new_id(), "run_id": run_id}
        )
        return run

    async def get(self, instance_id: str, run_id: str) -> RunDTO:
        async with self._uow_factory() as uow:
            return await self._owned_run(uow, instance_id, run_id)

    async def resume_instance(self, instance_id: str) -> None:
        async with self._uow_factory() as uow:
            run = await uow.runs.get_active_for_instance(instance_id)
        if run is not None and run.state in ACTIVE_STATES:
            self._scheduler.start(run.id)

    async def resume_all(self) -> None:
        async with self._uow_factory() as uow:
            runs = await uow.runs.list_active()
        for run in runs:
            self._scheduler.start(run.id)

    async def _start_run(
        self, uow: UnitOfWork, conversation_id: str, instance_id: str, now: datetime
    ) -> RunDTO:
        run = RunDTO(
            id=self._ids.new_id(),
            conversation_id=conversation_id,
            instance_id=instance_id,
            state=RunState.INTERVIEWING,
            created_at=now,
            updated_at=now,
        )
        await uow.runs.add(run)
        for previous in await uow.conversations.list_messages(conversation_id):
            await uow.runs.add_transcript(
                run.id,
                TranscriptEntry(
                    role=previous.role,
                    content=previous.content,
                    attachment_ids=previous.attachment_ids,
                ),
            )
        return run

    async def _answer_open_question(
        self, uow: UnitOfWork, run: RunDTO, text: str, attachment_ids: tuple[str, ...]
    ) -> bool:
        batch = await uow.runs.get_open_question_batch(run.id)
        if batch is None:
            return False
        await uow.runs.answer_question_batch(batch.id, text, self._clock.now())
        await uow.runs.add_transcript(
            run.id,
            TranscriptEntry(
                role="tool", content=text, tool_call_id=batch.call_id, attachment_ids=attachment_ids
            ),
        )
        return True

    async def _owned_run(
        self, uow: UnitOfWork, instance_id: str, run_id: str, *, lock: bool = False
    ) -> RunDTO:
        run = await uow.runs.get(run_id, lock=lock)
        if run is None or run.instance_id != instance_id:
            raise NotFound()
        return run


def _refusal(decision: Decision, fresh: bool, text: str | None) -> tuple[BatchStatus, str, str]:
    if decision is Decision.ACCEPT:
        return (
            BatchStatus.STALE,
            STALE_SCENE,
            "The scene changed before the confirmation; review the context and propose again.",
        )
    if decision is Decision.REJECT:
        return BatchStatus.REJECTED, "rejected_by_user", text or "The user rejected the batch."
    return BatchStatus.CLARIFIED, "clarification_requested", text or "The user asked to clarify."
