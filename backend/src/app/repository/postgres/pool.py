from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from app.repository.postgres.uow import PostgresUnitOfWork


async def open_pool(dsn: str, max_size: int) -> AsyncConnectionPool[AsyncConnection]:
    pool: AsyncConnectionPool[AsyncConnection] = AsyncConnectionPool(
        dsn, min_size=1, max_size=max_size, open=False
    )
    await pool.open(wait=True, timeout=30)
    return pool


class PostgresUnitOfWorkFactory:
    def __init__(self, pool: AsyncConnectionPool[AsyncConnection]) -> None:
        self._pool = pool

    def __call__(self) -> PostgresUnitOfWork:
        return PostgresUnitOfWork(self._pool)
