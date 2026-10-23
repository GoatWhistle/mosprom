import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from app.domain.confirmation import BatchStatus, Mode
from app.domain.run import RunState
from app.repository.postgres.pool import PostgresUnitOfWorkFactory
from app.usecase.dto.artifact import ArtifactBlob, ArtifactChunk, ArtifactDTO
from app.usecase.dto.conversation import (
    AttachmentBlob,
    AttachmentDTO,
    ConversationDTO,
    MessageDTO,
)
from app.usecase.dto.run import QuestionBatchDTO, RunDTO, TranscriptEntry
from app.usecase.dto.tools import CallStatus, ChangeBatchDTO, ToolCallDTO, ToolOutcome

pytestmark = pytest.mark.integration

NOW = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)
INSTANCE = "slicer-1"
CONVERSATION = "11111111-1111-1111-1111-111111111111"
RUN = "22222222-2222-2222-2222-222222222222"


def conversation(identifier: str = CONVERSATION, created: datetime = NOW) -> ConversationDTO:
    return ConversationDTO(
        id=identifier,
        instance_id=INSTANCE,
        title="t",
        mode=Mode.AUTO,
        created_at=created,
        updated_at=created,
    )


def run(identifier: str = RUN, state: RunState = RunState.INTERVIEWING) -> RunDTO:
    return RunDTO(
        id=identifier,
        conversation_id=CONVERSATION,
        instance_id=INSTANCE,
        state=state,
        created_at=NOW,
        updated_at=NOW,
    )


async def seed(factory: PostgresUnitOfWorkFactory) -> None:
    async with factory() as uow:
        await uow.instances.create(INSTANCE, "hash", NOW)
        await uow.conversations.create(conversation())
        await uow.runs.add(run())
        await uow.commit()


async def test_instance_token_lookup_and_duplicate(uow_factory: PostgresUnitOfWorkFactory) -> None:
    async with uow_factory() as uow:
        assert await uow.instances.create(INSTANCE, "hash", NOW)
        assert not await uow.instances.create(INSTANCE, "other", NOW)
        await uow.commit()
    async with uow_factory() as uow:
        found = await uow.instances.get_by_token_hash("hash")
        assert found is not None and found.id == INSTANCE
        assert await uow.instances.get_by_token_hash("missing") is None


async def test_snapshot_rejects_older_scene_version(uow_factory: PostgresUnitOfWorkFactory) -> None:
    await seed(uow_factory)
    async with uow_factory() as uow:
        assert await uow.instances.record_snapshot(INSTANCE, 3, {"a": 1}, NOW)
        assert not await uow.instances.record_snapshot(INSTANCE, 2, {"a": 0}, NOW)
        await uow.commit()
    async with uow_factory() as uow:
        instance = await uow.instances.get(INSTANCE)
        assert instance is not None
        assert instance.scene_version == 3 and instance.state == {"a": 1}


async def test_uncommitted_work_rolls_back(uow_factory: PostgresUnitOfWorkFactory) -> None:
    async with uow_factory() as uow:
        await uow.instances.create(INSTANCE, "hash", NOW)
    async with uow_factory() as uow:
        assert await uow.instances.get(INSTANCE) is None


async def test_one_active_run_per_instance(uow_factory: PostgresUnitOfWorkFactory) -> None:
    await seed(uow_factory)
    async with uow_factory() as uow:
        with pytest.raises(Exception, match="runs_one_active_per_instance"):
            await uow.runs.add(run("33333333-3333-3333-3333-333333333333"))


async def test_transition_is_conditional_and_recorded(
    uow_factory: PostgresUnitOfWorkFactory,
) -> None:
    await seed(uow_factory)
    async with uow_factory() as uow:
        assert await uow.runs.transition(
            RUN, RunState.INTERVIEWING, RunState.AWAITING_USER, "ask", NOW
        )
        assert not await uow.runs.transition(
            RUN, RunState.INTERVIEWING, RunState.FAILED, "late", NOW
        )
        await uow.commit()
    async with uow_factory() as uow:
        assert await uow.runs.list_transitions(RUN) == [("interviewing", "awaiting_user", "ask")]
        stored = await uow.runs.get(RUN)
        assert stored is not None and stored.state is RunState.AWAITING_USER


async def test_messages_keep_order_and_attachments(uow_factory: PostgresUnitOfWorkFactory) -> None:
    await seed(uow_factory)
    meta = AttachmentDTO(
        id="44444444-4444-4444-4444-444444444444",
        instance_id=INSTANCE,
        conversation_id=None,
        source="user",
        name="a.stl",
        content_type="model/stl",
        size=3,
        sha256=hashlib.sha256(b"abc").hexdigest(),
        created_at=NOW,
    )
    async with uow_factory() as uow:
        await uow.attachments.add(AttachmentBlob(meta=meta, data=b"abc"))
        for index in range(3):
            await uow.conversations.add_message(
                MessageDTO(
                    id=f"5555555{index}-5555-5555-5555-555555555555",
                    conversation_id=CONVERSATION,
                    run_id=RUN,
                    role="user",
                    content=str(index),
                    attachment_ids=(meta.id,) if index == 0 else (),
                    created_at=NOW,
                )
            )
        await uow.commit()
    async with uow_factory() as uow:
        messages = await uow.conversations.list_messages(CONVERSATION)
        assert [item.content for item in messages] == ["0", "1", "2"]
        assert messages[0].attachment_ids == (meta.id,)
        blob = await uow.attachments.get_blob(meta.id)
        assert blob is not None and blob.data == b"abc"


async def test_conversation_keyset_pagination(uow_factory: PostgresUnitOfWorkFactory) -> None:
    async with uow_factory() as uow:
        await uow.instances.create(INSTANCE, "hash", NOW)
        for index in range(5):
            await uow.conversations.create(
                conversation(
                    f"0000000{index}-0000-0000-0000-000000000000", NOW + timedelta(minutes=index)
                )
            )
        await uow.commit()
    async with uow_factory() as uow:
        first = await uow.conversations.list_page(INSTANCE, 2, None)
        last = first[-1]
        second = await uow.conversations.list_page(INSTANCE, 2, (last.created_at, last.id))
        assert [item.id[:8] for item in first] == ["00000004", "00000003"]
        assert [item.id[:8] for item in second] == ["00000002", "00000001"]


async def test_tool_call_completion_is_single_shot(uow_factory: PostgresUnitOfWorkFactory) -> None:
    await seed(uow_factory)
    call = ToolCallDTO(
        call_id="c1",
        run_id=RUN,
        llm_call_id="l1",
        tool="slice",
        arguments={},
        expected_scene_version=1,
        status=CallStatus.PENDING,
        created_at=NOW,
    )
    outcome = ToolOutcome(
        call_id="c1", ok=True, scene_version=2, result={"x": 1}, error=None, applied=({"op": 1},)
    )
    async with uow_factory() as uow:
        await uow.tool_calls.add(call)
        assert len(await uow.tool_calls.list_unfinished_for_instance(INSTANCE)) == 1
        assert await uow.tool_calls.complete(outcome, NOW)
        assert not await uow.tool_calls.mark_outcome_unknown("c1", NOW)
        await uow.commit()
    async with uow_factory() as uow:
        stored = await uow.tool_calls.get("c1")
        assert stored is not None
        assert stored.status is CallStatus.COMPLETED and stored.result == {"x": 1}
        assert stored.applied == ({"op": 1},)
        assert await uow.tool_calls.list_unfinished_for_instance(INSTANCE) == []


async def test_batch_status_changes_only_from_expected(
    uow_factory: PostgresUnitOfWorkFactory,
) -> None:
    await seed(uow_factory)
    batch = ChangeBatchDTO(
        id="66666666-6666-6666-6666-666666666666",
        run_id=RUN,
        call_id="c1",
        content_hash="h",
        scene_version=1,
        operations=({"kind": "arrange"},),
        explanation="why",
        status=BatchStatus.PROPOSED,
        created_at=NOW,
    )
    async with uow_factory() as uow:
        await uow.batches.add(batch)
        assert await uow.batches.set_status(
            batch.id, BatchStatus.PROPOSED, BatchStatus.ACCEPTED, None, NOW
        )
        assert not await uow.batches.set_status(
            batch.id, BatchStatus.PROPOSED, BatchStatus.REJECTED, None, NOW
        )
        await uow.commit()
    async with uow_factory() as uow:
        stored = await uow.batches.get(batch.id)
        assert stored is not None and stored.status is BatchStatus.ACCEPTED
        assert stored.operations == ({"kind": "arrange"},)


async def test_artifacts_round_trip_with_chunks(uow_factory: PostgresUnitOfWorkFactory) -> None:
    await seed(uow_factory)
    payload = bytes(range(256)) * 40
    digest = hashlib.sha256(payload).hexdigest()
    async with uow_factory() as uow:
        for index, part in enumerate((payload[:5000], payload[5000:])):
            await uow.artifacts.put_chunk(
                ArtifactChunk(
                    run_id=RUN,
                    kind="gcode",
                    scene_version=4,
                    chunk_index=index,
                    chunk_count=2,
                    sha256=hashlib.sha256(part).hexdigest(),
                    data=part,
                ),
                NOW,
            )
        await uow.commit()
    async with uow_factory() as uow:
        chunks = await uow.artifacts.list_chunks(RUN, "gcode", 4)
        assembled = b"".join(chunk.data for chunk in chunks)
        assert assembled == payload
        meta = ArtifactDTO(
            id="77777777-7777-7777-7777-777777777777",
            run_id=RUN,
            kind="gcode",
            scene_version=4,
            name="out.gcode",
            content_type="text/x.gcode",
            size=len(assembled),
            sha256=digest,
            created_at=NOW,
        )
        await uow.artifacts.save(ArtifactBlob(meta=meta, data=assembled))
        await uow.artifacts.delete_chunks(RUN, "gcode", 4)
        await uow.commit()
    async with uow_factory() as uow:
        assert await uow.artifacts.list_chunks(RUN, "gcode", 4) == []
        stored = await uow.artifacts.get_latest(RUN, "gcode")
        assert stored is not None and stored.data == payload and stored.meta.sha256 == digest


async def test_events_transcript_and_questions(uow_factory: PostgresUnitOfWorkFactory) -> None:
    await seed(uow_factory)
    async with uow_factory() as uow:
        first = await uow.runs.add_event(RUN, CONVERSATION, "a", {"n": 1}, NOW)
        second = await uow.runs.add_event(RUN, CONVERSATION, "b", {"n": 2}, NOW)
        assert second.id > first.id
        await uow.runs.add_transcript(RUN, TranscriptEntry(role="user", content="hi"))
        await uow.runs.add_question_batch(
            QuestionBatchDTO(
                id="88888888-8888-8888-8888-888888888888",
                run_id=RUN,
                call_id="c",
                questions=("q1", "q2"),
                answer=None,
                created_at=NOW,
            )
        )
        await uow.commit()
    async with uow_factory() as uow:
        assert [event.kind for event in await uow.runs.list_events(RUN)] == ["a", "b"]
        assert (await uow.runs.list_transcript(RUN))[0].content == "hi"
        open_batch = await uow.runs.get_open_question_batch(RUN)
        assert open_batch is not None and open_batch.questions == ("q1", "q2")
        await uow.runs.answer_question_batch(open_batch.id, "answer", NOW)
        assert await uow.runs.get_open_question_batch(RUN) is None
