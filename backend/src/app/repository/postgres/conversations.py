from datetime import datetime

from psycopg import AsyncConnection

from app.domain.confirmation import Mode
from app.usecase.dto.conversation import ConversationDTO, MessageDTO

CONVERSATION_COLUMNS = (
    "id, instance_id, title, mode, created_at, updated_at, project_state, project_version, "
    "project_sha256, project_saved_at"
)

INSERT = """
INSERT INTO conversations (id, instance_id, title, mode, created_at, updated_at)
VALUES (%(id)s, %(instance_id)s, %(title)s, %(mode)s, %(created_at)s, %(updated_at)s)
"""
SELECT = f"SELECT {CONVERSATION_COLUMNS} FROM conversations WHERE id = %(id)s"
LIST_FIRST = f"""
SELECT {CONVERSATION_COLUMNS} FROM conversations WHERE instance_id = %(instance_id)s
ORDER BY created_at DESC, id DESC LIMIT %(limit)s
"""
LIST_AFTER = f"""
SELECT {CONVERSATION_COLUMNS} FROM conversations
WHERE instance_id = %(instance_id)s AND (created_at, id) < (%(created_at)s, %(id)s)
ORDER BY created_at DESC, id DESC LIMIT %(limit)s
"""
SET_MODE = "UPDATE conversations SET mode = %(mode)s, updated_at = %(now)s WHERE id = %(id)s"
TOUCH = "UPDATE conversations SET updated_at = %(now)s WHERE id = %(id)s"
SET_PROJECT = """
UPDATE conversations SET project_state = %(state)s, project_sha256 = %(sha256)s,
    project_saved_at = %(now)s,
    project_version = CASE
        WHEN project_state = %(state)s AND project_sha256 IS NOT DISTINCT FROM %(sha256)s
        THEN project_version ELSE project_version + 1 END
WHERE id = %(id)s
RETURNING project_version
"""
INSERT_MESSAGE = """
INSERT INTO messages (id, conversation_id, run_id, role, content, created_at, client_message_id)
VALUES (%(id)s, %(conversation_id)s, %(run_id)s, %(role)s, %(content)s, %(created_at)s,
    %(client_message_id)s)
"""
FIND_BY_CLIENT_ID = """
SELECT m.id, m.conversation_id, m.run_id, m.role, m.content, m.created_at,
    COALESCE(
        (SELECT array_agg(ma.attachment_id::text ORDER BY ma.position)
         FROM message_attachments ma WHERE ma.message_id = m.id),
        ARRAY[]::text[]
    ),
    m.client_message_id
FROM messages m
WHERE m.conversation_id = %(conversation_id)s AND m.client_message_id = %(client_message_id)s
"""
LINK_ATTACHMENT = """
INSERT INTO message_attachments (message_id, attachment_id, position)
VALUES (%(message_id)s, %(attachment_id)s, %(position)s)
"""
LIST_MESSAGES = """
SELECT m.id, m.conversation_id, m.run_id, m.role, m.content, m.created_at,
    COALESCE(
        (SELECT array_agg(ma.attachment_id::text ORDER BY ma.position)
         FROM message_attachments ma WHERE ma.message_id = m.id),
        ARRAY[]::text[]
    )
FROM messages m WHERE m.conversation_id = %(conversation_id)s ORDER BY m.seq
"""


class PostgresConversationRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def create(self, conversation: ConversationDTO) -> None:
        await self._connection.execute(
            INSERT,
            {
                "id": conversation.id,
                "instance_id": conversation.instance_id,
                "title": conversation.title,
                "mode": conversation.mode.value,
                "created_at": conversation.created_at,
                "updated_at": conversation.updated_at,
            },
        )

    async def get(self, conversation_id: str) -> ConversationDTO | None:
        cursor = await self._connection.execute(SELECT, {"id": conversation_id})
        row = await cursor.fetchone()
        return _conversation(row) if row else None

    async def list_page(
        self, instance_id: str, limit: int, after: tuple[datetime, str] | None
    ) -> list[ConversationDTO]:
        if after is None:
            cursor = await self._connection.execute(
                LIST_FIRST, {"instance_id": instance_id, "limit": limit}
            )
        else:
            cursor = await self._connection.execute(
                LIST_AFTER,
                {
                    "instance_id": instance_id,
                    "limit": limit,
                    "created_at": after[0],
                    "id": after[1],
                },
            )
        return [_conversation(row) for row in await cursor.fetchall()]

    async def set_mode(self, conversation_id: str, mode: Mode, now: datetime) -> None:
        await self._connection.execute(
            SET_MODE, {"id": conversation_id, "mode": mode.value, "now": now}
        )

    async def set_project(
        self, conversation_id: str, state: str, sha256: str | None, now: datetime
    ) -> int:
        cursor = await self._connection.execute(
            SET_PROJECT, {"id": conversation_id, "state": state, "sha256": sha256, "now": now}
        )
        row = await cursor.fetchone()
        assert row is not None
        return int(str(row[0]))

    async def find_message_by_client_id(
        self, conversation_id: str, client_message_id: str
    ) -> MessageDTO | None:
        cursor = await self._connection.execute(
            FIND_BY_CLIENT_ID,
            {"conversation_id": conversation_id, "client_message_id": client_message_id},
        )
        row = await cursor.fetchone()
        return _message(row) if row else None

    async def touch(self, conversation_id: str, now: datetime) -> None:
        await self._connection.execute(TOUCH, {"id": conversation_id, "now": now})

    async def add_message(self, message: MessageDTO) -> None:
        await self._connection.execute(
            INSERT_MESSAGE,
            {
                "id": message.id,
                "conversation_id": message.conversation_id,
                "run_id": message.run_id,
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at,
                "client_message_id": message.client_message_id,
            },
        )
        for position, attachment_id in enumerate(message.attachment_ids):
            await self._connection.execute(
                LINK_ATTACHMENT,
                {"message_id": message.id, "attachment_id": attachment_id, "position": position},
            )

    async def list_messages(self, conversation_id: str) -> list[MessageDTO]:
        cursor = await self._connection.execute(LIST_MESSAGES, {"conversation_id": conversation_id})
        return [_message(row) for row in await cursor.fetchall()]


def _conversation(row: tuple[object, ...]) -> ConversationDTO:
    assert isinstance(row[4], datetime) and isinstance(row[5], datetime)
    return ConversationDTO(
        id=str(row[0]),
        instance_id=str(row[1]),
        title=str(row[2]),
        mode=Mode(str(row[3])),
        created_at=row[4],
        updated_at=row[5],
        project_state=str(row[6]),
        project_version=int(str(row[7])),
        project_sha256=str(row[8]) if row[8] is not None else None,
        project_saved_at=row[9] if isinstance(row[9], datetime) else None,
    )


def _message(row: tuple[object, ...]) -> MessageDTO:
    assert isinstance(row[5], datetime) and isinstance(row[6], list)
    return MessageDTO(
        id=str(row[0]),
        conversation_id=str(row[1]),
        run_id=str(row[2]) if row[2] else None,
        role=str(row[3]),
        content=str(row[4]),
        attachment_ids=tuple(str(item) for item in row[6]),
        created_at=row[5],
        client_message_id=str(row[7]) if len(row) > 7 and row[7] is not None else None,
    )
