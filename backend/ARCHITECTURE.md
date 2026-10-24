# Backend architecture

Read before implementing or restructuring the optional Claude proxy. Product architecture is in
`docs/architecture.md`; these engineering rules are removed from the submission copy.

## Current layout

Paths are relative to `backend/src/app/`.

| Area | Responsibility | Allowed project imports |
|---|---|---|
| `domain/` | Chat values, JSON types, errors | Domain |
| `usecase/` | Completion parsing/rendering and ports | Usecase, domain |
| `adapter/llm/` | Claude SDK, optional HTTP mirror, unavailable implementation | Adapter, usecase, domain |
| `adapter/log/` | Standard logging implementation | Adapter, usecase, domain |
| `controller/` | OpenAI-compatible routes, health, error mapping | Controller, usecase, domain |
| `main.py` | Settings, implementations, lifecycle, router composition | All runtime layers |

There is no repository layer implementation, database, migration system, backend agent loop or
WebSocket chat service. Chat state and tool execution belong to the STE plugin. Keep layer rules
if storage is later introduced; its design is a separate product decision.

## Dependency contract

Domain and usecase use Python values and dataclasses, never FastAPI, Pydantic or provider SDK types.
Outer layers do not import each other. Ports live under `usecase/interface/`; supply implementations
through constructors. Keep imports acyclic, including annotations and package re-exports.

`CompletionService` owns request parsing and response mapping. `ChatModel` accepts domain types;
`RequestMirror` receives the validated JSON body without controlling the main answer. Controller
code extracts the Bearer token and delegates; it does not construct SDK clients.

The exception to narrow typing is the SDK's dynamic message/structured output representation
inside its adapter. Keep it there; describe boundary changes in `docs/design-decisions.md`.

## Composition and lifecycle

`create_app()` reads `Settings`, registers health and `/v1` routers and error handlers. Lifespan
creates the Claude adapter (or `UnavailableChatModel` when the SDK is absent), mirror and
`CompletionService`, then closes external resources in `finally`.

The optional SDK import is lazy so a lean image can serve health and report an explicit unavailable
error for generation. The `llm` dependency group is installed by default locally and only with
`LLM=true` in Docker. The image uses the committed lock. Keep Buildx and Compose image names aligned.

Modules outside `adapter/log/` use the `Logger` port instead of importing logging. The architecture
test owns the exact import allowlist; update it only for an intentional dependency decision.

## Change placement and completion

- New API mapping: `controller/<subject>/`, with the contract in [API.md](API.md).
- New provider behavior: `adapter/<provider>/` behind a usecase port.
- Shared completion behavior: `usecase/`; pure values/errors: `domain/`.
- Concrete selection and configuration: `main.py` and `settings.py`.

After a change, run checks from [TESTING.md](TESTING.md) and update product documentation for changed
observable behavior. A passing fake-provider test does not prove a real Claude call.
