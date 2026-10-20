# Backend architecture

Read before implementing or restructuring backend code. Follow Clean Architecture: business rules
and use cases own their interfaces; outer modules implement transport and external dependencies.

## Layout

Paths below are relative to `backend/`. The scaffold uses `app` as its default package name. Use it
consistently in the future manifest, imports, startup command and tests; rename it together if the
project chooses another name. Create subject modules as the real scenario requires them.

```text
backend/
  AGENTS.md
  ARCHITECTURE.md
  API.md
  DATABASE.md
  TESTING.md
  src/app/
    domain/
    usecase/
    repository/
      postgres/
    adapter/
    controller/
  migrations/
    postgres/
  tests/
    domain/
    usecase/
    repository/
      postgres/
    adapter/
    controller/
    architecture/
    e2e/
  scripts/
  benchmarks/
```

Each empty leaf folder contains `.gitkeep` so Git can preserve the layout. Remove that file when
adding actual content. During bootstrap, add `pyproject.toml`, `uv.lock`, `Dockerfile`, the
dbmate `migrate` Compose service and package modules. The template already ships `Dockerfile`,
the `backend` Compose service, `src/app/main.py` and `src/app/settings.py`.

The Markdown instructions are internal and scrubbed before submission. Runtime source, migrations,
tests and project configuration ship. Benchmarks and scripts call the same use cases as the
product. Reference material stays outside the runtime package and is read only by its explicit owner.

## Responsibilities and imports

| Module | Owns | Allowed project dependencies |
| --- | --- | --- |
| `domain` | Entities, value objects, business invariants, state transitions, pure calculations, domain errors | `domain` |
| `usecase` | Use cases, commands/results, DTOs, authorization decisions, ports, Unit of Work port | `usecase`, `domain` |
| `repository` | Persistence: connections, SQL queries, row-to-DTO mapping, Unit of Work, stored files | `repository`, `usecase`, `domain` |
| `adapter` | External clients and provider implementations: LLM, embeddings, HTTP APIs, queues, file import | `adapter`, `usecase`, `domain` |
| `controller` | HTTP routes, Pydantic schemas, request/result mapping, authentication extraction, HTTP error mapping | `controller`, `usecase`, `domain` |
| `main.py` | Configuration, concrete dependency construction, lifecycle, router registration | All runtime modules |

`domain` and `usecase` use ordinary Python types and `dataclasses`. They do not import FastAPI,
Pydantic, database drivers, provider SDKs, `repository`, `adapter`, `controller` or `main.py`. Pure
computation libraries require an explicit project decision when standard Python is insufficient.
Dependencies stay acyclic, including imports used only for annotations or hidden inside functions.

`controller`, `repository` and `adapter` do not import each other; they meet only through `usecase`
ports. The composition root is the place that knows all of them. Internal calculations stay inside
their owning module; an interface is needed where a use case depends on an external capability.

## Domain

- Express business invariants next to the entity or value they protect, using domain language from
  `docs/glossary.md`. Reuse the same rule for HTTP, seed scripts, workers and command-line entry points.
- Reject invalid transitions before mutating state. Domain errors describe the business failure,
  without HTTP statuses or localized text.
- Use a pure domain function for a rule spanning several entities. Give its file the subject's name.
- Time, randomness and identifiers affecting business behavior arrive as values or supplied
  dependencies; pure rules do not reach for environment variables, global clocks or network clients.

## Use cases

- A use case represents a user or system action with a small typed input and result. It loads the
  required state, checks the actor's access, invokes domain rules and coordinates persistence.
- Declare ports as typed protocols in `usecase/interface.py`; split it into `usecase/interface/`
  by subject when it outgrows the file limit. Name methods after required operations; expose domain
  values or use case results.
- Keep connections, driver rows, HTTP requests/responses and provider objects outside port
  signatures. Commands, results and DTOs are dataclasses without framework validation behavior.
  Repository DTOs live in `usecase/dto.py` (see [DATABASE.md](DATABASE.md)).
- Supply repositories, transaction scopes, providers and clocks through constructors. Construction
  does not select implementations or perform I/O.
- The use case owns the consistency boundary. It opens a Unit of Work per operation and commits
  through it; controllers, repositories and domain entities do not commit.

## Repositories, adapters and controllers

- Map SQL rows to DTOs inside the repository; no ORM is used. Map external provider responses inside
  that provider's adapter. Translate storage- and provider-specific failures into failures defined
  by the port.
- Repositories implement persistence/query operations, one folder per storage
  (`repository/postgres/`, `repository/sqlite/`, `repository/memory/`). Adapters implement non-storage external
  capabilities. Repositories and adapters do not call each other; a use case coordinates both.
- Decisions about allowed business actions remain in the domain and use cases; database
  constraints support those rules under concurrency.
- HTTP schemas live in `controller/`. Validate request shape there, invoke the use case and map its
  result to an explicit response schema. HTTP mapping is specified in [API.md](API.md).
- Keep parsing and persistence models separate even when they initially share fields. Public input
  must not become a stored row or select arbitrary stored columns.

## Composition and lifecycle

- `main.py` is the composition root: read configuration, choose implementations, build use cases
  and register their routers. Use ordinary factories and constructors for wiring.
- Database pools and provider clients are started and closed through the application lifecycle.
  Transaction/session resources have request or operation scope, not shared mutable global state.
- A worker or script may have its own entry point and reuse common composition functions. It calls
  the same use case interfaces; it does not depend on HTTP controllers.
- Add a separate composition module when wiring outgrows `main.py`. Domain and usecase modules
  never import the composition root, including through re-exports in `__init__.py`.

## Where new code belongs

| Change | Location |
| --- | --- |
| New invariant or state transition | `domain/<subject>.py` |
| New action or access decision | `usecase/<subject>.py` |
| Port required by an action | `usecase/interface.py` |
| SQL query, row mapping or Unit of Work | `repository/<storage>/` |
| Repository DTO | `usecase/dto.py` |
| Vector similarity search (numpy matrix, pgvector) | Vector index in `repository/`, behind a port |
| In-memory or file storage | `repository/memory/`, `repository/files.py` |
| External provider implementation | `adapter/<provider>/` |
| HTTP endpoint or schema | `controller/<subject>/` |
| Schema change | `migrations/<storage>/`, created by `dbmate new` |
| Concrete dependency selection | `main.py` or composition module |

Use subject names within each layer. A new generic `models/` or `service/` bucket obscures whether
code owns domain rules, transport, persistence or orchestration; place it by that responsibility.
Enforce the import contract as described in [TESTING.md](TESTING.md).
