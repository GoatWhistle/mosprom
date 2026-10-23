from typing import Self

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from app.repository.postgres.artifacts import PostgresArtifactRepository
from app.repository.postgres.attachments import PostgresAttachmentRepository
from app.repository.postgres.batches import PostgresChangeBatchRepository
from app.repository.postgres.conversations import PostgresConversationRepository
from app.repository.postgres.instances import PostgresInstanceRepository
from app.repository.postgres.runs import PostgresRunRepository
from app.repository.postgres.tool_calls import PostgresToolCallRepository
from app.usecase.interface.storage import (
    ArtifactRepository,
    AttachmentRepository,
    ChangeBatchRepository,
    ConversationRepository,
    InstanceRepository,
    RunRepository,
    ToolCallRepository,
)


class PostgresUnitOfWork:
    instances: InstanceRepository
    conversations: ConversationRepository
    attachments: AttachmentRepository
    runs: RunRepository
    tool_calls: ToolCallRepository
    batches: ChangeBatchRepository
    artifacts: ArtifactRepository

    def __init__(self, pool: AsyncConnectionPool[AsyncConnection]) -> None:
        self._pool = pool
        self._connection: AsyncConnection | None = None
        self._committed = False

    async def __aenter__(self) -> Self:
        connection = await self._pool.getconn()
        self._connection = connection
        self.instances = PostgresInstanceRepository(connection)
        self.conversations = PostgresConversationRepository(connection)
        self.attachments = PostgresAttachmentRepository(connection)
        self.runs = PostgresRunRepository(connection)
        self.tool_calls = PostgresToolCallRepository(connection)
        self.batches = PostgresChangeBatchRepository(connection)
        self.artifacts = PostgresArtifactRepository(connection)
        return self

    async def __aexit__(self, *exc: object) -> None:
        connection = self._connection
        if connection is None:
            return
        try:
            if not self._committed:
                await connection.rollback()
        finally:
            self._connection = None
            await self._pool.putconn(connection)

    async def commit(self) -> None:
        if self._connection is None or self._committed:
            raise RuntimeError("Unit of work is not open or already committed")
        await self._connection.commit()
        self._committed = True
