from collections.abc import Sequence
from datetime import datetime

from psycopg import AsyncConnection

from app.usecase.dto.conversation import AttachmentBlob, AttachmentDTO

META = "id, instance_id, conversation_id, source, name, content_type, size, sha256, created_at"
INSERT = """
INSERT INTO attachments
    (id, instance_id, conversation_id, source, name, content_type, size, sha256, data, created_at)
VALUES (%(id)s, %(instance_id)s, %(conversation_id)s, %(source)s, %(name)s, %(content_type)s,
    %(size)s, %(sha256)s, %(data)s, %(created_at)s)
"""
SELECT_BLOB = f"SELECT {META}, data FROM attachments WHERE id = %(id)s"
LINK = "UPDATE attachments SET conversation_id = %(conversation_id)s WHERE id = ANY(%(ids)s)"
LIST_FOR_CONVERSATION = (
    f"SELECT {META} FROM attachments WHERE conversation_id = %(conversation_id)s "
    "ORDER BY created_at, id"
)


class PostgresAttachmentRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def add(self, blob: AttachmentBlob) -> None:
        meta = blob.meta
        await self._connection.execute(
            INSERT,
            {
                "id": meta.id,
                "instance_id": meta.instance_id,
                "conversation_id": meta.conversation_id,
                "source": meta.source,
                "name": meta.name,
                "content_type": meta.content_type,
                "size": meta.size,
                "sha256": meta.sha256,
                "data": blob.data,
                "created_at": meta.created_at,
            },
        )

    async def get_blob(self, attachment_id: str) -> AttachmentBlob | None:
        cursor = await self._connection.execute(SELECT_BLOB, {"id": attachment_id})
        row = await cursor.fetchone()
        if row is None:
            return None
        return AttachmentBlob(meta=_meta(row), data=bytes(row[9]))

    async def link(self, attachment_ids: Sequence[str], conversation_id: str) -> None:
        await self._connection.execute(
            LINK, {"conversation_id": conversation_id, "ids": list(attachment_ids)}
        )

    async def list_for_conversation(self, conversation_id: str) -> list[AttachmentDTO]:
        cursor = await self._connection.execute(
            LIST_FOR_CONVERSATION, {"conversation_id": conversation_id}
        )
        return [_meta(row) for row in await cursor.fetchall()]


def _meta(row: tuple[object, ...]) -> AttachmentDTO:
    assert isinstance(row[8], datetime)
    return AttachmentDTO(
        id=str(row[0]),
        instance_id=str(row[1]),
        conversation_id=str(row[2]) if row[2] else None,
        source=str(row[3]),
        name=str(row[4]),
        content_type=str(row[5]),
        size=int(str(row[6])),
        sha256=str(row[7]),
        created_at=row[8],
    )
