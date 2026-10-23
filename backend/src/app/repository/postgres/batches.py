from datetime import datetime

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from app.domain.confirmation import BatchStatus
from app.usecase.dto.tools import ChangeBatchDTO

COLUMNS = (
    "id, run_id, call_id, content_hash, scene_version, operations, explanation, status, "
    "decision_text, created_at"
)
INSERT = """
INSERT INTO change_batches (id, run_id, call_id, content_hash, scene_version, operations,
    explanation, status, decision_text, created_at)
VALUES (%(id)s, %(run_id)s, %(call_id)s, %(content_hash)s, %(scene_version)s, %(operations)s,
    %(explanation)s, %(status)s, %(decision_text)s, %(created_at)s)
"""
SELECT = f"SELECT {COLUMNS} FROM change_batches WHERE id = %(id)s"
SELECT_PROPOSED = (
    f"SELECT {COLUMNS} FROM change_batches WHERE run_id = %(run_id)s AND status = 'proposed' "
    "ORDER BY created_at DESC LIMIT 1"
)
SELECT_ACCEPTED = (
    f"SELECT {COLUMNS} FROM change_batches WHERE run_id = %(run_id)s AND status = 'accepted' "
    "ORDER BY created_at DESC LIMIT 1"
)
SET_STATUS = """
UPDATE change_batches SET status = %(new)s, decision_text = %(decision_text)s,
    decided_at = %(now)s
WHERE id = %(id)s AND status = %(expected)s
RETURNING id
"""


class PostgresChangeBatchRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def add(self, batch: ChangeBatchDTO) -> None:
        await self._connection.execute(
            INSERT,
            {
                "id": batch.id,
                "run_id": batch.run_id,
                "call_id": batch.call_id,
                "content_hash": batch.content_hash,
                "scene_version": batch.scene_version,
                "operations": Jsonb(list(batch.operations)),
                "explanation": batch.explanation,
                "status": batch.status.value,
                "decision_text": batch.decision_text,
                "created_at": batch.created_at,
            },
        )

    async def get(self, batch_id: str) -> ChangeBatchDTO | None:
        cursor = await self._connection.execute(SELECT, {"id": batch_id})
        row = await cursor.fetchone()
        return _batch(row) if row else None

    async def get_proposed_for_run(self, run_id: str) -> ChangeBatchDTO | None:
        cursor = await self._connection.execute(SELECT_PROPOSED, {"run_id": run_id})
        row = await cursor.fetchone()
        return _batch(row) if row else None

    async def get_accepted_for_run(self, run_id: str) -> ChangeBatchDTO | None:
        cursor = await self._connection.execute(SELECT_ACCEPTED, {"run_id": run_id})
        row = await cursor.fetchone()
        return _batch(row) if row else None

    async def set_status(
        self,
        batch_id: str,
        expected: BatchStatus,
        new: BatchStatus,
        decision_text: str | None,
        now: datetime,
    ) -> bool:
        cursor = await self._connection.execute(
            SET_STATUS,
            {
                "id": batch_id,
                "expected": expected.value,
                "new": new.value,
                "decision_text": decision_text,
                "now": now,
            },
        )
        return await cursor.fetchone() is not None


def _batch(row: tuple[object, ...]) -> ChangeBatchDTO:
    assert isinstance(row[5], list) and isinstance(row[9], datetime)
    return ChangeBatchDTO(
        id=str(row[0]),
        run_id=str(row[1]),
        call_id=str(row[2]),
        content_hash=str(row[3]),
        scene_version=int(str(row[4])),
        operations=tuple(item for item in row[5] if isinstance(item, dict)),
        explanation=str(row[6]),
        status=BatchStatus(str(row[7])),
        decision_text=str(row[8]) if row[8] is not None else None,
        created_at=row[9],
    )
