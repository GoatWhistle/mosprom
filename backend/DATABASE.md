# Backend persistence

Read before changing storage, repositories, migrations, transactions or seed data. Layer ownership
follows [ARCHITECTURE.md](ARCHITECTURE.md).

## Choose the storage first

Before writing the first repository, ask the user which storage the project needs, and wait for the
answer: in-memory only, or a database (SQLite or PostgreSQL). Do not pick one silently. Record the
answer in `docs/adr/`, the `context/README.md` facts and `docs/architecture.md`.

| Storage | Fits | Consequences |
| --- | --- | --- |
| `memory` | Demo without durable state, data rebuilt on every start | No migrations; seed runs at startup through use cases; restart loses data; state lives in one process |
| `sqlite` | Single-process stand, durable file, no extra service | dbmate SQL migrations; database file in a named volume; one writer at a time |
| `postgres` | Concurrent writes, several processes, jury load, pgvector | dbmate SQL migrations; PostgreSQL 16 service |

A database project still keeps the in-memory implementation when unit tests of use cases need fast
fakes; it passes the same contract tests (see [Contract tests](#contract-tests)).

## Repository rules

- **No ORM.** Repositories run hand-written SQL through the driver: `psycopg` 3 with `psycopg_pool`
  for PostgreSQL, `aiosqlite` for SQLite. SQLAlchemy, SQLModel, Tortoise, Peewee and query builders
  are not used, including SQLAlchemy Core.
- **No Pydantic in persistence.** DTOs, rows and settings consumed by repositories are standard
  `dataclasses`. Pydantic stays at the HTTP edge in `controller/` (see [API.md](API.md)).
- **DTO at the port.** Repository methods accept and return DTOs: `@dataclass(frozen=True,
  slots=True, kw_only=True)` without behavior, defined in `usecase/dto.py` (split into
  `usecase/dto/<subject>.py` when it grows). A DTO describes what the use case needs, not the table.
  Driver rows, cursors, connections and `dict` rows never cross the port. The use case maps a DTO to
  a domain entity when business rules apply.
- **Unit of Work.** Use cases receive a UoW factory and open one UoW per operation. Repositories are
  reachable only through it; they never open connections, commit or roll back.
- One repository per aggregate or read model, named after the subject (`OrderRepository`). Methods
  match real scenario operations (`get_for_owner`, `list_open_page`, `mark_paid_if_pending`). No
  generic `BaseRepository`, CRUD mixin or `filter(**kwargs)` method.
- Write SQL as module-level constants next to the repository that runs it. List columns
  explicitly; never `SELECT *`. Map columns to DTO fields in one place per query.
- Pass every value through driver placeholders (`%(name)s` in psycopg, `:name` in SQLite). Dynamic
  identifiers or `ORDER BY` come from an explicit allowlist; user input never becomes SQL text.
- Avoid N+1: load related rows with one query (`= ANY(%(ids)s)`, `JOIN`) and write batches with
  `executemany`. Use `RETURNING` instead of a follow-up `SELECT`.
- Paginate with a keyset (`WHERE (created_at, id) < (...)`) on lists that may grow; return a page
  DTO with items and the next cursor.
- Store time as UTC: `timestamptz` in PostgreSQL, ISO-8601 UTC text in SQLite. Identifiers that
  affect behavior come from the use case or a supplied generator, not from the repository.
- Translate known constraint violations by constraint name into failures declared next to the port.
  Let unrelated database errors propagate.
- Choose async access, matching FastAPI. Blocking calls never run directly on the event loop.

## Unit of Work

The port lives in `usecase/interface.py` with the repository protocols it exposes:

```python
class UnitOfWork(Protocol):
    orders: OrderRepository

    async def __aenter__(self) -> Self: ...
    async def __aexit__(self, *exc: object) -> None: ...
    async def commit(self) -> None: ...


UnitOfWorkFactory = Callable[[], UnitOfWork]
```

```python
async with self._uow() as uow:
    order = await uow.orders.get_for_owner(order_id, actor_id)
    ...
    await uow.commit()
```

- Leaving the block without `commit()`, or with an exception, rolls back. Read-only use cases open
  a UoW and do not commit. A committed UoW is not reused.
- The use case defines what is atomic. Several repositories inside one UoW share its transaction.
- Implementations: `repository/postgres/uow.py` takes a connection from the pool and starts a
  transaction; `repository/sqlite/uow.py` opens the connection with `BEGIN IMMEDIATE` for writes;
  `repository/memory/uow.py` works on a copy of the state, swaps it in on commit and serializes
  writers with an `asyncio.Lock`. All three give the same rollback semantics.
- Keep external network calls outside an open UoW. If a scenario needs persistence and an external
  effect, define retry/idempotency and the failure state before implementation; record it in an ADR
  when warranted.

## Concurrency and constraints

- State checks followed by writes stay valid under concurrent requests. Use constraints,
  conditional updates (`UPDATE ... WHERE status = 'pending' RETURNING`), version columns or
  `SELECT ... FOR UPDATE`; an earlier unlocked read is not a guarantee.
- Constraints protect uniqueness, references and value bounds. Name them explicitly so repositories
  can map them to port failures.
- Retried actions and seed operations do not duplicate effects. Add an idempotency key when the
  scenario needs a durable retry guarantee, not on every endpoint.
- Pools live for the application lifetime and close at shutdown. SQLite connections enable
  `PRAGMA foreign_keys = ON`, `journal_mode = WAL` and a `busy_timeout`.

## Migrations

- Migrations are plain SQL files applied by [dbmate](https://github.com/amacneil/dbmate). No Alembic,
  no Python migration code and no schema generated from code.
- Files live in `backend/migrations/<storage>/`, one dialect per folder, created with
  `dbmate -d migrations/<storage> new <slug>` (timestamped `YYYYMMDDHHMMSS_<slug>.sql`). Each file
  has a `-- migrate:up` section and a `-- migrate:down` section; dbmate runs every file in a
  transaction and records it in `schema_migrations`.
- Compose runs a one-shot `migrate` service from `ghcr.io/amacneil/dbmate:2.36.0` with
  `DATABASE_URL`, `DBMATE_MIGRATIONS_DIR`, `DBMATE_NO_DUMP_SCHEMA=true`, `DBMATE_STRICT=true` and
  `DBMATE_WAIT=true`; PostgreSQL also sets `DBMATE_MIGRATION_LOCK=true`. The backend depends on it
  with `condition: service_completed_successfully`. Request handlers and workers do not create
  tables. For SQLite the service mounts the same named volume as the backend
  (`DATABASE_URL=sqlite:/data/app.db`).
- A shared or deployed file is immutable; a correction is a new file. `down` sections are for local
  rollback only. A rewritten local chain is validated on a fresh disposable database.
- Assess defaults, nullability, uniqueness, indexes and existing data together. Data conversion is
  SQL in the same sequence. SQLite PRAGMAs that cannot run in a transaction use
  `-- migrate:up transaction:false`. Document any irreversible or destructive step.
- Integration tests build the schema with `dbmate --url <test url> up` on the same files and fail
  clearly when the `dbmate` binary is missing.

## Seed data

- One documented command seeds synthetic demo data into the chosen storage by calling use cases,
  preserving business rules and permissions. For `memory`, `main.py` runs the same seed at startup.
- Unit test fixtures stay in `tests/`. Demo source records may live in an explicitly named data file
  read by the seed command; they are never returned as canned API responses.
- Stable seed identifiers and `ON CONFLICT DO NOTHING` make the command repeatable. Mark demo data
  as synthetic in product documentation.
- For a database, seeding is an explicit command; startup does not silently populate it.

## Contract tests

Write behavior tests for each repository port once, as functions that receive a UoW factory. Run
them against every implementation the project keeps: `memory` in `tests/unit/repository/memory/`,
`sqlite` (temporary file) and `postgres` in `tests/integration/repository/<storage>/`, both with
the schema applied by dbmate. A fake that
diverges from the database fails the same test. Details are in [TESTING.md](TESTING.md).

## Product documentation

Document the chosen storage, connection settings and seed/migration commands in `docs/running.md`,
persistence ownership in `docs/architecture.md`, the storage decision in `docs/adr/`, and the
in-memory data loss in `docs/limitations.md` when applicable. These files remain after the internal
instructions are removed.
