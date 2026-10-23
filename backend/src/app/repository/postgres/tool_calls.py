from datetime import datetime

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from app.domain.jsonvalue import JsonObject
from app.usecase.dto.tools import CallStatus, ToolCallDTO, ToolOutcome

COLUMNS = (
    "call_id, run_id, llm_call_id, tool, arguments, expected_scene_version, status, batch_id, "
    "result, error, applied, scene_version, created_at, finished_at"
)
INSERT = """
INSERT INTO tool_calls (call_id, run_id, llm_call_id, tool, arguments, expected_scene_version,
    status, batch_id, created_at)
VALUES (%(call_id)s, %(run_id)s, %(llm_call_id)s, %(tool)s, %(arguments)s,
    %(expected_scene_version)s, %(status)s, %(batch_id)s, %(created_at)s)
"""
SELECT = f"SELECT {COLUMNS} FROM tool_calls WHERE call_id = %(call_id)s"
MARK_SENT = """
UPDATE tool_calls SET status = 'sent', sent_at = %(now)s
WHERE call_id = %(call_id)s AND status IN ('pending', 'sent')
"""
COMPLETE = """
UPDATE tool_calls SET status = %(status)s, result = %(result)s, error = %(error)s,
    applied = %(applied)s, scene_version = %(scene_version)s, finished_at = %(now)s
WHERE call_id = %(call_id)s AND status IN ('pending', 'sent', 'outcome_unknown')
RETURNING call_id
"""
MARK_UNKNOWN = """
UPDATE tool_calls SET status = 'outcome_unknown', finished_at = %(now)s
WHERE call_id = %(call_id)s AND status IN ('pending', 'sent')
RETURNING call_id
"""
LIST_UNFINISHED = f"""
SELECT {", ".join("t." + name.strip() for name in COLUMNS.split(","))}
FROM tool_calls t JOIN runs r ON r.id = t.run_id
WHERE r.instance_id = %(instance_id)s AND t.status IN ('pending', 'sent')
ORDER BY t.created_at
"""
LIST_FOR_RUN = f"SELECT {COLUMNS} FROM tool_calls WHERE run_id = %(run_id)s ORDER BY created_at"
SAVE_SLICE_JOB = """
INSERT INTO slice_jobs (run_id, call_id, scene_version, status, metrics, created_at)
VALUES (%(run_id)s, %(call_id)s, %(scene_version)s, %(status)s, %(metrics)s, %(now)s)
ON CONFLICT ON CONSTRAINT slice_jobs_call_key DO UPDATE
SET status = EXCLUDED.status, metrics = EXCLUDED.metrics, scene_version = EXCLUDED.scene_version
"""


class PostgresToolCallRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def add(self, call: ToolCallDTO) -> None:
        await self._connection.execute(
            INSERT,
            {
                "call_id": call.call_id,
                "run_id": call.run_id,
                "llm_call_id": call.llm_call_id,
                "tool": call.tool,
                "arguments": Jsonb(call.arguments),
                "expected_scene_version": call.expected_scene_version,
                "status": call.status.value,
                "batch_id": call.batch_id,
                "created_at": call.created_at,
            },
        )

    async def get(self, call_id: str) -> ToolCallDTO | None:
        cursor = await self._connection.execute(SELECT, {"call_id": call_id})
        row = await cursor.fetchone()
        return _call(row) if row else None

    async def mark_sent(self, call_id: str, now: datetime) -> None:
        await self._connection.execute(MARK_SENT, {"call_id": call_id, "now": now})

    async def complete(self, outcome: ToolOutcome, now: datetime) -> bool:
        cursor = await self._connection.execute(
            COMPLETE,
            {
                "call_id": outcome.call_id,
                "status": (CallStatus.COMPLETED if outcome.ok else CallStatus.FAILED).value,
                "result": Jsonb(outcome.result),
                "error": Jsonb(outcome.error) if outcome.error is not None else None,
                "applied": Jsonb(list(outcome.applied)),
                "scene_version": outcome.scene_version,
                "now": now,
            },
        )
        return await cursor.fetchone() is not None

    async def mark_outcome_unknown(self, call_id: str, now: datetime) -> bool:
        cursor = await self._connection.execute(MARK_UNKNOWN, {"call_id": call_id, "now": now})
        return await cursor.fetchone() is not None

    async def list_unfinished_for_instance(self, instance_id: str) -> list[ToolCallDTO]:
        cursor = await self._connection.execute(LIST_UNFINISHED, {"instance_id": instance_id})
        return [_call(row) for row in await cursor.fetchall()]

    async def list_for_run(self, run_id: str) -> list[ToolCallDTO]:
        cursor = await self._connection.execute(LIST_FOR_RUN, {"run_id": run_id})
        return [_call(row) for row in await cursor.fetchall()]

    async def save_slice_job(
        self,
        run_id: str,
        call_id: str,
        scene_version: int,
        status: str,
        metrics: JsonObject,
        now: datetime,
    ) -> None:
        await self._connection.execute(
            SAVE_SLICE_JOB,
            {
                "run_id": run_id,
                "call_id": call_id,
                "scene_version": scene_version,
                "status": status,
                "metrics": Jsonb(metrics),
                "now": now,
            },
        )


def _call(row: tuple[object, ...]) -> ToolCallDTO:
    assert isinstance(row[4], dict) and isinstance(row[10], list) and isinstance(row[12], datetime)
    return ToolCallDTO(
        call_id=str(row[0]),
        run_id=str(row[1]),
        llm_call_id=str(row[2]),
        tool=str(row[3]),
        arguments=row[4],
        expected_scene_version=int(str(row[5])),
        status=CallStatus(str(row[6])),
        batch_id=str(row[7]) if row[7] is not None else None,
        result=row[8] if isinstance(row[8], dict) else None,
        error=row[9] if isinstance(row[9], dict) else None,
        applied=tuple(item for item in row[10] if isinstance(item, dict)),
        scene_version=int(str(row[11])) if row[11] is not None else None,
        created_at=row[12],
        finished_at=row[13] if isinstance(row[13], datetime) else None,
    )
