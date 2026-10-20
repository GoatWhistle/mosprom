# Template development archive

This records work on the template itself, not instructions for a new hackathon.

# Session state

Updated: 2026-10-14, Europe/Moscow.

The user's explicit instructions and the current state of the work, so the next session continues
without asking again. Instructions here outrank skill defaults; `AGENTS.md` outranks this file.

## Explicit user instructions

One bullet per instruction, close to the user's own words, with the date. Remove an instruction only
when the user withdraws or replaces it, and say which one replaced it. Compaction never touches this
section.

- 2026-10-12: Rework the whole hackathon template in the `refactor/template` branch.
- 2026-10-12: Keep one root `skills/` source, referenced by both Claude Code and Codex.
- 2026-10-13: Keep backend instructions as organized Markdown files inside `backend/`; remove
  them through the submission cleanup script. Use Clean Architecture with `domain`, `application`,
  `adapter`, `controller` and `main.py` under `src/app/`. Layer names replaced on 2026-10-14 below.
- 2026-10-13: Create the backend folder layout now and preserve empty folders with `.gitkeep`.
- 2026-10-14: Commit all current template changes and push the `refactor/template` branch.
- 2026-10-14: «сделай слой repository и вынесы из adapter postgres»; «application переименой в
  usecase»; reference layout: `tender/.claude/worktrees/clean-arch/src/rag`. Layers are now
  `domain`, `usecase`, `repository`, `adapter`, `controller`; branch `refactor/backend-layers`.
- 2026-10-14: «давай сразу добавим интерфейсы для эмбедера и llm» from the same tender reference;
  branch `feat/backend-inference-ports`.
- 2026-10-14: «добавим сразу адаптер под claude agent sdk», taken from tender history
  (`db97ea7^:src/rag/adapter/llm/claude_agent.py`); added to PR #4.
- 2026-10-14: «Нужно тесты бэкенда поделить на интеграционные и на unit и чтобы в precommit только
  unit запускались, причем быстро и желательно паралельно»; branch `test/backend-unit-split`.
- 2026-10-14: «Давай добавим адаптер для codex agents sdk, сначала прочитай его доку»; branch
  `feat/backend-codex-adapter`. Docs read from `openai/codex` `sdk/python`; SDK `openai-codex` 0.162.1.
- 2026-10-14: «Давай добавим правила как писать репозитории: 1. Никаких ORM, только sql 2. Миграции
  тоже в orm формате 3. Использовать DTO 4. Никакого pydatinc только dataclass 5. Паттерн UoW
  6. Справшивай нужно только in memory или всё таки бд (sqlite, pg)». Item 2 read as SQL migration
  files; rules in `backend/DATABASE.md`; branch `docs/backend-repository-rules`.
- 2026-10-14: «dbmate, pydantic в контроллерах оставь, пушь». Migrations use dbmate 2.36.0; Pydantic
  stays for HTTP schemas in `controller/`.
- 2026-10-14: «как сейчас выглядит точка сборки приложения?» → «делай». FastAPI composition root
  `main.py` + `settings.py`, `/api/health`, error envelope, backend Dockerfile and Compose service;
  no storage (DATABASE.md requires asking first); branch `feat/backend-composition-root`.
- 2026-10-15: Decks: «слишком длинное название слайда», «получаются одинаковые», «желательно
  больше сотни слайдов… с графиками, визуализациями, анимациями», «не должно быть неявных
  слайдов… прослистнул дальше и там появилось что-то на слайде», «несколько слайдов отображения
  команды». Titles are capped at 40 characters by the build, steps are banned by the build, the
  library has 150 layouts with the `data-viz` chart engine and six team layouts.
- 2026-10-15: «добавь еще 50 слайдов… потом пройдись по каждому из 200… пустоты, анимации,
  визуал, приятность, гармоничность… поштучно, по второму кругу». Library grew to 200 layouts
  (151–200); every layout was reviewed frame by frame and fixed; catalog lists all 200.

## Current state

- **Branch and build:** `refactor/template`; backend scaffold committed as `ee9ef76`. Remaining structural changes
  are being committed and pushed. Links, syntax and context budget pass; no runtime suite was run.
- **Stand:** The template has a frontend Compose service, backend instructions and an empty
  `src/app/` scaffold; no backend runtime, manifest, database service or domain scenario has been
  bootstrapped.
- **Current task:** Backend instructions are split by architecture, API, persistence and testing.
  The layer and test folders exist with `.gitkeep`; the default package name is `app`.

## How to continue

Continue reviewing the template's rules with the user. Read `backend/AGENTS.md` and the document
matching the next backend topic. The organizer brief is still a template; current work is on the
template itself rather than a specific hackathon scenario.

## Pitfalls already hit

- Skill aliases have different path depth from their source. Read skill resources from canonical
  `skills/<name>/`; references outside a skill name paths from the repository root.

## Done

- Shared root skill sources and discovery symlinks for both agents are present.
- Backend instruction layout and dependency contract are written in `backend/AGENTS.md` and
  `backend/ARCHITECTURE.md`, with topic rules in `API.md`, `DATABASE.md` and `TESTING.md`. The four
  topic documents are listed in `.claude/scrub-paths` for submission cleanup.
- Backend source layers, PostgreSQL repository folder, migrations, tests by layer, scripts and
  benchmarks are scaffolded with `.gitkeep`, included in `ee9ef76`.

## Left, in order

1. Review the backend rules and agree on any further conventions before bootstrapping runtime code.
2. Cleanup review found reproducible defects, still unfixed: file edits can follow a symlink
   outside the repository, history cleanup leaves annotated tag messages, and the separate-copy
   scrubber preserves ordinary commit bodies. Reproductions used isolated repositories.
3. Memory-workflow improvements were proposed, not implemented: startup pointers for both agents,
   persistent handoff, budget overflow handling, required-file checks and brief lifecycle rules.

## Red checks

- No backend runtime check results: the implementation and its tooling do not exist yet.

## Current revision

- 2026-10-14: Fix cleanup, documentation, agent startup and overlapping skill discovery.
- Keep the backend as an empty Clean Architecture scaffold; runtime bootstrapping is excluded.
- The development branch is `refactor/template`; obtain its current SHA with `git rev-parse HEAD`.

## Completed workflow review

- Root startup instructions are explicit for both agents; GitHub tracking is optional and handoff is persistent.
- Initial context files are neutral templates; the previous development state is archived above.
- Product design decisions ship. Internal screen specs and audits live in `work/`.
- Jury questions and pitch evidence use `presentation/jury-qa.md` and `presentation/pitch-evidence.md`.
- Skill descriptions are concise; vendor overlaps are manual in both agents and the redundant wrapper is removed.
- One cleanup engine handles tree cleanup and bare history export, with safety preflight and verification.
- Backend runtime remains excluded by the user's 2026-10-14 instruction.
- Verification details: [workflow audit](audits/2026-10-14-template.md).
