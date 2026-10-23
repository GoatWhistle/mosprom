from collections.abc import Sequence
from datetime import datetime

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from app.domain.jsonvalue import JsonObject
from app.usecase.dto.instance import InstanceDTO

COLUMNS = (
    "id, token_hash, slicer_version, printer, modes, scene_version, state, "
    "contract_version, last_seen_at, scene_epoch, active_conversation_id"
)

INSERT = """
INSERT INTO instances (id, token_hash, registered_at)
VALUES (%(id)s, %(token_hash)s, %(now)s)
ON CONFLICT (id) DO NOTHING
RETURNING id
"""
SELECT_BY_ID = f"SELECT {COLUMNS} FROM instances WHERE id = %(id)s"
SELECT_BY_TOKEN = f"SELECT {COLUMNS} FROM instances WHERE token_hash = %(token_hash)s"
RECORD_HELLO = """
UPDATE instances SET slicer_version = %(slicer_version)s, modes = %(modes)s,
    scene_version = CASE WHEN scene_epoch = %(scene_epoch)s THEN scene_version ELSE 0 END,
    state = CASE WHEN scene_epoch = %(scene_epoch)s THEN state ELSE '{}'::jsonb END,
    scene_epoch = %(scene_epoch)s, printer = %(printer)s, contract_version = %(contract_version)s, last_seen_at = %(now)s
WHERE id = %(id)s
"""
SET_ACTIVE = "UPDATE instances SET active_conversation_id = %(conversation_id)s WHERE id = %(id)s"
LOCK = "SELECT scene_version, scene_epoch FROM instances WHERE id = %(id)s FOR UPDATE"
UPDATE_SNAPSHOT = """
UPDATE instances SET scene_version = %(scene_version)s, state = %(state)s, last_seen_at = %(now)s
WHERE id = %(id)s
"""
INSERT_SNAPSHOT = """
INSERT INTO state_snapshots (instance_id, scene_version, state, created_at, scene_epoch)
VALUES (%(id)s, %(scene_version)s, %(state)s, %(now)s, %(scene_epoch)s)
"""
ADVANCE = """
UPDATE instances SET scene_version = GREATEST(scene_version, %(scene_version)s)
WHERE id = %(id)s AND scene_epoch = %(scene_epoch)s
"""


class PostgresInstanceRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def create(self, instance_id: str, token_hash: str, now: datetime) -> bool:
        cursor = await self._connection.execute(
            INSERT, {"id": instance_id, "token_hash": token_hash, "now": now}
        )
        return await cursor.fetchone() is not None

    async def get(self, instance_id: str) -> InstanceDTO | None:
        cursor = await self._connection.execute(SELECT_BY_ID, {"id": instance_id})
        row = await cursor.fetchone()
        return _to_dto(row) if row else None

    async def get_by_token_hash(self, token_hash: str) -> InstanceDTO | None:
        cursor = await self._connection.execute(SELECT_BY_TOKEN, {"token_hash": token_hash})
        row = await cursor.fetchone()
        return _to_dto(row) if row else None

    async def record_hello(
        self,
        instance_id: str,
        *,
        slicer_version: str,
        modes: Sequence[str],
        printer: JsonObject,
        contract_version: str,
        now: datetime,
        scene_epoch: str = "",
    ) -> None:
        await self._connection.execute(
            RECORD_HELLO,
            {
                "id": instance_id,
                "slicer_version": slicer_version,
                "modes": Jsonb(list(modes)),
                "printer": Jsonb(printer),
                "contract_version": contract_version,
                "scene_epoch": scene_epoch,
                "now": now,
            },
        )

    async def record_snapshot(
        self,
        instance_id: str,
        scene_version: int,
        state: JsonObject,
        now: datetime,
        scene_epoch: str = "",
    ) -> bool:
        cursor = await self._connection.execute(LOCK, {"id": instance_id})
        row = await cursor.fetchone()
        if row is None or row[1] != scene_epoch or scene_version < int(row[0]):
            return False
        params = {
            "id": instance_id,
            "scene_version": scene_version,
            "state": Jsonb(state),
            "scene_epoch": scene_epoch,
            "now": now,
        }
        await self._connection.execute(UPDATE_SNAPSHOT, params)
        await self._connection.execute(INSERT_SNAPSHOT, params)
        return True

    async def set_active_conversation(self, instance_id: str, conversation_id: str | None) -> None:
        await self._connection.execute(
            SET_ACTIVE, {"id": instance_id, "conversation_id": conversation_id}
        )

    async def advance_scene_version(
        self, instance_id: str, scene_version: int, scene_epoch: str = ""
    ) -> None:
        await self._connection.execute(
            ADVANCE, {"id": instance_id, "scene_version": scene_version, "scene_epoch": scene_epoch}
        )


def _to_dto(row: tuple[object, ...]) -> InstanceDTO:
    return InstanceDTO(
        scene_epoch=str(row[9]),
        id=str(row[0]),
        token_hash=str(row[1]),
        slicer_version=row[2] if isinstance(row[2], str) else None,
        printer=row[3] if isinstance(row[3], dict) else {},
        modes=tuple(str(item) for item in row[4]) if isinstance(row[4], list) else (),
        scene_version=int(str(row[5])),
        state=row[6] if isinstance(row[6], dict) else {},
        contract_version=row[7] if isinstance(row[7], str) else None,
        last_seen_at=row[8] if isinstance(row[8], datetime) else None,
        active_conversation_id=str(row[10]) if row[10] is not None else None,
    )
