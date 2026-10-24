# Backend validation

Read before adding tests or reporting backend verification. All current backend tests live in
`tests/unit/`; there is no integration directory or database. Product commands are in
`docs/running.md` and the manual acceptance procedure is in `docs/validation-plan.md`.

## Coverage by responsibility

| Area | What tests exercise | What they do not prove |
|---|---|---|
| Completion | OpenAI message/tool/image mapping and fixed model selection | Provider quality or full API compatibility |
| Claude adapter | SDK options, output mapping, timeout and malformed responses; query is replaced | Authentication and real inference |
| Mirror | HTTP payload, failures and shutdown; MockTransport | Availability or quota of the real mirror |
| Composition | Environment parsing, lifecycle and mirror isolation | Container networking or deployment |
| Errors | Status and response mapping, safe error fields | All third-party log contents |
| Architecture | Imports for every module under src/app | Runtime concurrency behavior |

SDK types are imported by tests, so the `llm` group must be installed even though network calls are
replaced. Default `uv sync --locked` includes it. No automatic test calls a paid provider.

## Commands

From `backend/`:

```bash
uv sync --locked
uv run ruff check .
uv run mypy .
uv run pytest tests/unit
```

`pytest` passes `-n auto`; `tests/conftest.py` chooses workers according to the collected file count.
Use `-n 0` to force serial execution. Declare new test dependencies in pyproject and update the lock.
An empty or missing integration directory is not a successful integration run.

Tests mirror the owning layer. Use deterministic provider responses or local protocol servers.
Check observable behavior, failures and cancellation instead of copying implementation details.
The import test parses the entire runtime package and prevents domain/usecase imports of frameworks,
outer-layer imports of each other, cycles and logging outside its adapter.

## Reporting

Record the command, Python version, commit and passed/skipped counts. Report the real provider and
stand only after an explicit manual run, with inputs and limitations. For documentation-only changes,
check links, commands and cleanup paths; do not add redundant unit tests.

The STE plugin has a separate suite:
`cd plugin && PYTHONPATH=. python3 -B -m unittest discover -s tests -t .` from the repository root.
It uses fake slicer adapters and local scripted LLM responses; real Qt and 5D validation remains a
stand task. Pre-commit runs backend unit tests when backend files are staged.
