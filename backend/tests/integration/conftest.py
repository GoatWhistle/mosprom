import subprocess
import time
import uuid
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from app.repository.postgres.pool import PostgresUnitOfWorkFactory

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations" / "postgres"
POSTGRES_IMAGE = "postgres:16"
DBMATE_IMAGE = "ghcr.io/amacneil/dbmate:2.36.0"
PASSWORD = "test"


def docker(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=False)


@pytest.fixture(scope="session")
def postgres_dsn() -> Iterator[str]:
    name = f"brim-test-{uuid.uuid4().hex[:8]}"
    started = docker(
        "run",
        "-d",
        "--rm",
        "--name",
        name,
        "-e",
        f"POSTGRES_PASSWORD={PASSWORD}",
        "-p",
        "127.0.0.1::5432",
        POSTGRES_IMAGE,
    )
    if started.returncode != 0:
        pytest.fail(f"docker is required for integration tests: {started.stderr.strip()}")
    try:
        port = docker("port", name, "5432/tcp").stdout.split(":")[-1].strip()
        deadline = time.monotonic() + 60
        while docker("exec", name, "pg_isready", "-U", "postgres").returncode != 0:
            if time.monotonic() > deadline:
                pytest.fail("postgres did not become ready")
            time.sleep(0.5)
        migrated = docker(
            "run",
            "--rm",
            "--network",
            f"container:{name}",
            "-v",
            f"{MIGRATIONS}:/db/migrations:ro",
            "-e",
            f"DATABASE_URL=postgres://postgres:{PASSWORD}@127.0.0.1:5432/postgres?sslmode=disable",
            "-e",
            "DBMATE_NO_DUMP_SCHEMA=true",
            "-e",
            "DBMATE_STRICT=true",
            "-e",
            "DBMATE_WAIT=true",
            "-e",
            "DBMATE_MIGRATION_LOCK=true",
            DBMATE_IMAGE,
            "up",
        )
        if migrated.returncode != 0:
            pytest.fail(f"dbmate failed: {migrated.stdout}{migrated.stderr}")
        yield f"postgresql://postgres:{PASSWORD}@127.0.0.1:{port}/postgres"
    finally:
        docker("stop", name)


@pytest_asyncio.fixture
async def pool(postgres_dsn: str) -> AsyncIterator[AsyncConnectionPool[AsyncConnection]]:
    async with AsyncConnectionPool(postgres_dsn, min_size=1, max_size=8, open=False) as pool:
        await pool.wait()
        async with pool.connection() as connection:
            await connection.execute(
                "TRUNCATE instances, state_snapshots, conversations, attachments, runs, messages, "
                "message_attachments, run_transitions, run_events, agent_transcript, "
                "requirement_batches, change_batches, tool_calls, slice_jobs, artifacts, "
                "artifact_chunks CASCADE"
            )
        yield pool


@pytest.fixture
def uow_factory(pool: AsyncConnectionPool[AsyncConnection]) -> PostgresUnitOfWorkFactory:
    return PostgresUnitOfWorkFactory(pool)
