from datetime import datetime

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from app.domain.jsonvalue import JsonObject
from app.domain.run import ACTIVE_STATES, RunState
from app.repository.postgres.run_mapping import _entry, _entry_json, _params, _run
from app.usecase.dto.run import QuestionBatchDTO, RunDTO, RunEventDTO, TranscriptEntry

COLUMNS = (
    "id, conversation_id, instance_id, state, requirements_ready, requirements_summary, "
    "correction_key, correction_failures, help_required, steps, last_error, created_at, "
    "updated_at, finished_at, project_version"
)
ACTIVE = [state.value for state in ACTIVE_STATES]

INSERT = """
INSERT INTO runs (id, conversation_id, instance_id, state, requirements_ready,
    requirements_summary, correction_key, correction_failures, help_required, steps, last_error,
    created_at, updated_at, finished_at, project_version)
VALUES (%(id)s, %(conversation_id)s, %(instance_id)s, %(state)s, %(requirements_ready)s,
    %(requirements_summary)s, %(correction_key)s, %(correction_failures)s, %(help_required)s,
    %(steps)s, %(last_error)s, %(created_at)s, %(updated_at)s, %(finished_at)s, %(project_version)s)
"""
SELECT = f"SELECT {COLUMNS} FROM runs WHERE id = %(id)s"
SELECT_LOCKED = f"{SELECT} FOR UPDATE"
SELECT_ACTIVE_FOR_INSTANCE = (
    f"SELECT {COLUMNS} FROM runs WHERE instance_id = %(instance_id)s AND state = ANY(%(active)s)"
)
SELECT_ACTIVE = f"SELECT {COLUMNS} FROM runs WHERE state = ANY(%(active)s) ORDER BY created_at"
SELECT_LATEST = (
    f"SELECT {COLUMNS} FROM runs WHERE conversation_id = %(conversation_id)s "
    "ORDER BY created_at DESC, id DESC LIMIT 1"
)
UPDATE = """
UPDATE runs SET state = %(state)s, requirements_ready = %(requirements_ready)s,
    requirements_summary = %(requirements_summary)s, correction_key = %(correction_key)s,
    correction_failures = %(correction_failures)s, help_required = %(help_required)s,
    steps = %(steps)s, last_error = %(last_error)s, updated_at = %(updated_at)s,
    finished_at = %(finished_at)s, project_version = %(project_version)s
WHERE id = %(id)s
"""
TRANSITION = """
UPDATE runs SET state = %(target)s, updated_at = %(now)s,
    finished_at = CASE WHEN %(target)s IN ('completed', 'failed', 'aborted')
        THEN %(now)s ELSE finished_at END
WHERE id = %(id)s AND state = %(expected)s
RETURNING id
"""
INSERT_TRANSITION = """
INSERT INTO run_transitions (run_id, from_state, to_state, reason, created_at)
VALUES (%(id)s, %(expected)s, %(target)s, %(reason)s, %(now)s)
"""
LIST_TRANSITIONS = (
    "SELECT from_state, to_state, reason FROM run_transitions WHERE run_id = %(id)s ORDER BY id"
)
INSERT_EVENT = """
INSERT INTO run_events (run_id, conversation_id, kind, payload, created_at)
VALUES (%(run_id)s, %(conversation_id)s, %(kind)s, %(payload)s, %(now)s)
RETURNING id
"""
LIST_EVENTS = """
SELECT id, run_id, conversation_id, kind, payload, created_at
FROM run_events WHERE run_id = %(run_id)s ORDER BY id
"""
INSERT_TRANSCRIPT = "INSERT INTO agent_transcript (run_id, entry) VALUES (%(run_id)s, %(entry)s)"
LIST_TRANSCRIPT = "SELECT entry FROM agent_transcript WHERE run_id = %(run_id)s ORDER BY id"
INSERT_QUESTIONS = """
INSERT INTO requirement_batches (id, run_id, call_id, questions, created_at)
VALUES (%(id)s, %(run_id)s, %(call_id)s, %(questions)s, %(created_at)s)
"""
SELECT_OPEN_QUESTIONS = """
SELECT id, run_id, call_id, questions, answer, created_at FROM requirement_batches
WHERE run_id = %(run_id)s AND answer IS NULL ORDER BY created_at DESC LIMIT 1
"""
ANSWER_QUESTIONS = (
    "UPDATE requirement_batches SET answer = %(answer)s, answered_at = %(now)s WHERE id = %(id)s"
)


class PostgresRunRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def add(self, run: RunDTO) -> None:
        await self._connection.execute(INSERT, _params(run))

    async def get(self, run_id: str, *, lock: bool = False) -> RunDTO | None:
        cursor = await self._connection.execute(SELECT_LOCKED if lock else SELECT, {"id": run_id})
        row = await cursor.fetchone()
        return _run(row) if row else None

    async def get_active_for_instance(self, instance_id: str) -> RunDTO | None:
        cursor = await self._connection.execute(
            SELECT_ACTIVE_FOR_INSTANCE, {"instance_id": instance_id, "active": ACTIVE}
        )
        row = await cursor.fetchone()
        return _run(row) if row else None

    async def get_latest_for_conversation(self, conversation_id: str) -> RunDTO | None:
        cursor = await self._connection.execute(SELECT_LATEST, {"conversation_id": conversation_id})
        row = await cursor.fetchone()
        return _run(row) if row else None

    async def update(self, run: RunDTO) -> None:
        await self._connection.execute(UPDATE, _params(run))

    async def transition(
        self, run_id: str, expected: RunState, target: RunState, reason: str, now: datetime
    ) -> bool:
        params = {
            "id": run_id,
            "expected": expected.value,
            "target": target.value,
            "reason": reason,
            "now": now,
        }
        cursor = await self._connection.execute(TRANSITION, params)
        if await cursor.fetchone() is None:
            return False
        await self._connection.execute(INSERT_TRANSITION, params)
        return True

    async def list_transitions(self, run_id: str) -> list[tuple[str, str, str]]:
        cursor = await self._connection.execute(LIST_TRANSITIONS, {"id": run_id})
        return [(str(row[0]), str(row[1]), str(row[2])) for row in await cursor.fetchall()]

    async def list_active(self) -> list[RunDTO]:
        cursor = await self._connection.execute(SELECT_ACTIVE, {"active": ACTIVE})
        return [_run(row) for row in await cursor.fetchall()]

    async def add_event(
        self, run_id: str, conversation_id: str, kind: str, payload: JsonObject, now: datetime
    ) -> RunEventDTO:
        cursor = await self._connection.execute(
            INSERT_EVENT,
            {
                "run_id": run_id,
                "conversation_id": conversation_id,
                "kind": kind,
                "payload": Jsonb(payload),
                "now": now,
            },
        )
        row = await cursor.fetchone()
        assert row is not None
        return RunEventDTO(
            id=int(row[0]),
            run_id=run_id,
            conversation_id=conversation_id,
            kind=kind,
            payload=payload,
            created_at=now,
        )

    async def list_events(self, run_id: str) -> list[RunEventDTO]:
        cursor = await self._connection.execute(LIST_EVENTS, {"run_id": run_id})
        events = []
        for row in await cursor.fetchall():
            assert isinstance(row[4], dict) and isinstance(row[5], datetime)
            events.append(
                RunEventDTO(
                    id=int(row[0]),
                    run_id=str(row[1]),
                    conversation_id=str(row[2]),
                    kind=str(row[3]),
                    payload=row[4],
                    created_at=row[5],
                )
            )
        return events

    async def add_transcript(self, run_id: str, entry: TranscriptEntry) -> None:
        await self._connection.execute(
            INSERT_TRANSCRIPT, {"run_id": run_id, "entry": Jsonb(_entry_json(entry))}
        )

    async def list_transcript(self, run_id: str) -> list[TranscriptEntry]:
        cursor = await self._connection.execute(LIST_TRANSCRIPT, {"run_id": run_id})
        return [_entry(row[0]) for row in await cursor.fetchall()]

    async def add_question_batch(self, batch: QuestionBatchDTO) -> None:
        await self._connection.execute(
            INSERT_QUESTIONS,
            {
                "id": batch.id,
                "run_id": batch.run_id,
                "call_id": batch.call_id,
                "questions": Jsonb(list(batch.questions)),
                "created_at": batch.created_at,
            },
        )

    async def get_open_question_batch(self, run_id: str) -> QuestionBatchDTO | None:
        cursor = await self._connection.execute(SELECT_OPEN_QUESTIONS, {"run_id": run_id})
        row = await cursor.fetchone()
        if row is None:
            return None
        assert isinstance(row[3], list) and isinstance(row[5], datetime)
        return QuestionBatchDTO(
            id=str(row[0]),
            run_id=str(row[1]),
            call_id=str(row[2]),
            questions=tuple(str(item) for item in row[3]),
            answer=None,
            created_at=row[5],
        )

    async def answer_question_batch(self, batch_id: str, answer: str, now: datetime) -> None:
        await self._connection.execute(
            ANSWER_QUESTIONS, {"id": batch_id, "answer": answer, "now": now}
        )
