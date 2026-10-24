# Backend rules

Read this file before backend work. The [root instructions](../AGENTS.md) also apply, including
code style, language, file limits and the requirement to use real logic and storage.

## Read by task

| Before | Read |
| --- | --- |
| Any backend implementation or refactor | [ARCHITECTURE.md](ARCHITECTURE.md): layers, imports, ports and composition |
| Changing routes, schemas, errors or authentication | [API.md](API.md): HTTP contracts and permission handling |
| Adding or changing tests, or reporting validation | [TESTING.md](TESTING.md): test scope and checks |

Read every matching document when a task spans several areas. These three files are internal working
instructions removed at submission. Product documentation lives in `docs/` and describes the
implemented system; product files must not link to these internal instructions.

## Brim backend today

The backend is an optional stateless proxy for Claude by subscription: `controller/openai/router.py`
serves `POST /v1/chat/completions` and `GET /v1/models` in the OpenAI format, `usecase/completion.py`
maps OpenAI messages to `domain/chat.py`, and `adapter/llm/claude_agent.py` calls Claude Agent SDK
with the request's Bearer token. The `/v1` router is mounted next to `api_router_v1` because OpenAI
clients append `/chat/completions` to their base URL. There is no database, WebSocket or agent loop
here; the agent runs in `plugin/Brim/agent/`. Never log the Bearer token.
When `MIRROR_*` is set, `adapter/llm/openai_mirror.py` fire-and-forgets each valid request to an
OpenAI-compatible endpoint (the organizers' Qwen) through the `RequestMirror` port; its answer is
never used.

## Architecture contract

- Use `src/app/{domain,usecase,repository,adapter,controller}` and a `main.py` composition root.
  `app` is the template's default package name. If renamed during kickoff, update paths, imports,
  startup commands and package configuration together.
- `domain` owns business rules; `usecase` owns use cases and ports. Neither imports framework,
  persistence or provider code. `repository` implements storage ports (`repository/<storage>/`),
  `adapter` implements external providers, `controller` owns HTTP. These three never import each
  other.
- Supply dependencies through use case constructors. Concrete implementations are selected at
  startup in `main.py`; controllers call use cases rather than storage or provider SDKs.
- Type hints are required. Explain any necessary `Any` in `docs/design-decisions.md`.
- External providers have a deterministic implementation for the main offline scenario. It computes
  from the input and real stored data. Missing implementations produce an honest error.
- Secrets come from environment variables, with safe defaults in `.env.example`. The stand starts
  without `.env` and releases resources at shutdown.

## Default stack

Unless the task or an explicit project decision chooses otherwise: Python 3.12+, FastAPI,
Pydantic only for HTTP schemas in `controller/`, standard `dataclasses` everywhere else, uv, Ruff
with line length 100, mypy strict and pytest.

Brim has no persistence since ADR 0002 (2026-10-23): chat history and files live in the plugin and
DATABASE.md was removed. If storage returns, ask the user whether it is in-memory only or a
database (SQLite or PostgreSQL 16) before the first repository; no ORM, only
SQL through the driver; SQL migrations applied by dbmate in a one-shot Compose service; dataclass DTOs
at repository ports; Unit of Work for transactions.

The current backend ports are `ChatModel`, `RequestMirror` and `Logger` under `usecase/interface/`.
`CompletionService` parses OpenAI-shaped JSON into domain chat types and renders the result.
`ClaudeAgentChatAdapter` uses Claude Agent SDK; `UnavailableChatModel` reports a clear error when
that optional dependency is absent. There is no offline generation fallback in the current proxy.
The mirror is optional and cannot affect the main response. Logging goes through `Logger`;
`adapter/log/stdlib.py` owns the standard logging dependency.

`create_app()` reads settings, registers `/api/v1/health` and the `/v1` router, and creates the
completion service and clients in lifespan. Both model and mirror close on shutdown. The image
installs the committed lock; `claude-agent-sdk` belongs to the `llm` group, installed locally by
default and in Docker only with `LLM=true`. Keep `COMPOSE_PROJECT_NAME` and `TAG` aligned between
Bake and Compose. Use the current commands in TESTING.md; no integration directory exists today.
