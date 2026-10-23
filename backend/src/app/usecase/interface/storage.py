from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Protocol, Self

from app.domain.confirmation import BatchStatus, Mode
from app.domain.jsonvalue import JsonObject
from app.domain.run import RunState
from app.usecase.dto.artifact import ArtifactBlob, ArtifactChunk, ArtifactDTO
from app.usecase.dto.conversation import (
    AttachmentBlob,
    AttachmentDTO,
    ConversationDTO,
    MessageDTO,
)
from app.usecase.dto.instance import InstanceDTO
from app.usecase.dto.run import QuestionBatchDTO, RunDTO, RunEventDTO, TranscriptEntry
from app.usecase.dto.tools import ChangeBatchDTO, ToolCallDTO, ToolOutcome


class InstanceRepository(Protocol):
    async def create(self, instance_id: str, token_hash: str, now: datetime) -> bool: ...

    async def get(self, instance_id: str) -> InstanceDTO | None: ...

    async def get_by_token_hash(self, token_hash: str) -> InstanceDTO | None: ...

    async def record_hello(
        self,
        instance_id: str,
        *,
        slicer_version: str,
        modes: Sequence[str],
        printer: JsonObject,
        contract_version: str,
        now: datetime,
    ) -> None: ...

    async def record_snapshot(
        self, instance_id: str, scene_version: int, state: JsonObject, now: datetime
    ) -> bool: ...

    async def advance_scene_version(self, instance_id: str, scene_version: int) -> None: ...


class ConversationRepository(Protocol):
    async def create(self, conversation: ConversationDTO) -> None: ...

    async def get(self, conversation_id: str) -> ConversationDTO | None: ...

    async def list_page(
        self, instance_id: str, limit: int, after: tuple[datetime, str] | None
    ) -> list[ConversationDTO]: ...

    async def set_mode(self, conversation_id: str, mode: Mode, now: datetime) -> None: ...

    async def touch(self, conversation_id: str, now: datetime) -> None: ...

    async def add_message(self, message: MessageDTO) -> None: ...

    async def list_messages(self, conversation_id: str) -> list[MessageDTO]: ...


class AttachmentRepository(Protocol):
    async def add(self, blob: AttachmentBlob) -> None: ...

    async def get_blob(self, attachment_id: str) -> AttachmentBlob | None: ...

    async def link(self, attachment_ids: Sequence[str], conversation_id: str) -> None: ...

    async def list_for_conversation(self, conversation_id: str) -> list[AttachmentDTO]: ...


class RunRepository(Protocol):
    async def add(self, run: RunDTO) -> None: ...

    async def get(self, run_id: str, *, lock: bool = False) -> RunDTO | None: ...

    async def get_active_for_instance(self, instance_id: str) -> RunDTO | None: ...

    async def update(self, run: RunDTO) -> None: ...

    async def transition(
        self, run_id: str, expected: RunState, target: RunState, reason: str, now: datetime
    ) -> bool: ...

    async def list_transitions(self, run_id: str) -> list[tuple[str, str, str]]: ...

    async def list_active(self) -> list[RunDTO]: ...

    async def add_event(
        self, run_id: str, conversation_id: str, kind: str, payload: JsonObject, now: datetime
    ) -> RunEventDTO: ...

    async def list_events(self, run_id: str) -> list[RunEventDTO]: ...

    async def add_transcript(self, run_id: str, entry: TranscriptEntry) -> None: ...

    async def list_transcript(self, run_id: str) -> list[TranscriptEntry]: ...

    async def add_question_batch(self, batch: QuestionBatchDTO) -> None: ...

    async def get_open_question_batch(self, run_id: str) -> QuestionBatchDTO | None: ...

    async def answer_question_batch(self, batch_id: str, answer: str, now: datetime) -> None: ...


class ToolCallRepository(Protocol):
    async def add(self, call: ToolCallDTO) -> None: ...

    async def get(self, call_id: str) -> ToolCallDTO | None: ...

    async def mark_sent(self, call_id: str, now: datetime) -> None: ...

    async def complete(self, outcome: ToolOutcome, now: datetime) -> bool: ...

    async def mark_outcome_unknown(self, call_id: str, now: datetime) -> bool: ...

    async def list_unfinished_for_instance(self, instance_id: str) -> list[ToolCallDTO]: ...

    async def list_for_run(self, run_id: str) -> list[ToolCallDTO]: ...

    async def save_slice_job(
        self,
        run_id: str,
        call_id: str,
        scene_version: int,
        status: str,
        metrics: JsonObject,
        now: datetime,
    ) -> None: ...


class ChangeBatchRepository(Protocol):
    async def add(self, batch: ChangeBatchDTO) -> None: ...

    async def get(self, batch_id: str) -> ChangeBatchDTO | None: ...

    async def get_proposed_for_run(self, run_id: str) -> ChangeBatchDTO | None: ...

    async def get_accepted_for_run(self, run_id: str) -> ChangeBatchDTO | None: ...

    async def set_status(
        self,
        batch_id: str,
        expected: BatchStatus,
        new: BatchStatus,
        decision_text: str | None,
        now: datetime,
    ) -> bool: ...


class ArtifactRepository(Protocol):
    async def lock(self, run_id: str, kind: str, scene_version: int) -> None: ...

    async def put_chunk(self, chunk: ArtifactChunk, now: datetime) -> None: ...

    async def list_chunks(
        self, run_id: str, kind: str, scene_version: int
    ) -> list[ArtifactChunk]: ...

    async def delete_chunks(self, run_id: str, kind: str, scene_version: int) -> None: ...

    async def save(self, blob: ArtifactBlob) -> None: ...

    async def get_latest(self, run_id: str, kind: str) -> ArtifactBlob | None: ...

    async def list_meta(self, run_id: str) -> list[ArtifactDTO]: ...


class UnitOfWork(Protocol):
    instances: InstanceRepository
    conversations: ConversationRepository
    attachments: AttachmentRepository
    runs: RunRepository
    tool_calls: ToolCallRepository
    batches: ChangeBatchRepository
    artifacts: ArtifactRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(self, *exc: object) -> None: ...

    async def commit(self) -> None: ...


UnitOfWorkFactory = Callable[[], UnitOfWork]
