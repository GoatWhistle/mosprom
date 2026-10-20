# {{PRODUCT}} — {{one-line positioning}}

{{HACKATHON}}, track {{TRACK}}. Deadline: {{date, time, timezone}}.
{{User, product action and observable benefit. Fill during hackathon kickoff.}}

## Start a session

1. Read `context/README.md`, `context/SESSION.md` and `context/open-questions.md` before acting.
   Claude's SessionStart hook injects them; Codex reads them explicitly. These files contain state,
   not workflow rules. Preserve active user instructions word for word.
2. Read the area's `AGENTS.md` before touching `frontend/`, `backend/` or `presentation/`.
   For work on this template itself, consult `work/template-development.md`; its history does not
   become instructions for a new hackathon.
3. Use the skills required by the task, from canonical `skills/<name>/`. Load supporting references
   only when their branch applies. Skill recommendations yield to project rules and user instructions.
4. For a new hackathon or a changed organizer brief, use `hack-kickoff`. Template maintenance and
   ordinary edits can proceed with the available information while missing facts are recorded.

## Sources of truth

| What | Where and when to read |
|---|---|
| Original task, organizer answers, platform and event | `brief/README.md`, then the relevant source |
| Criteria and weights | `brief/requirements.md`, for scope and priorities |
| Current state, instructions, unresolved questions | The three `context/` files, at session start |
| Domain vocabulary | `docs/glossary.md`; this is the `GLOSSARY.md` named by skills |
| Durable decisions and uncommented code explanations | `docs/adr/`, `docs/design-decisions.md` |
| Product documentation and measured claims | `docs/README.md`, `docs/evidence.md` |
| Internal working artifacts | `work/README.md`, by pointer |
| UI / backend / defense rules | `frontend/AGENTS.md` / `backend/AGENTS.md` / `presentation/AGENTS.md` |

On conflict: organizer originals, then `brief/QA.md`, then derived brief views, then product docs.
A newer official source supersedes an older answer; record source, date and page. Label assumptions.
Originals and verbatim quotes are preserved; derived views may be updated with their citations.

## Priorities and architecture

- P0 is the scenario the jury will use. Order work by criteria weights; finish P0 before P1/P2.
- Frontend: React, Vite and TypeScript. Backend: Clean Architecture under
  `src/app/{domain,usecase,repository,adapter,controller}`, wired in `main.py`. Outer layers depend
  on domain/usecase interfaces. Read the backend topic documents before implementation.
- The current template has frontend and backend Compose services. The backend has LLM/embedding
  ports with Claude Agent SDK and Codex SDK adapters, a decision-model port with a System One HTTP
  adapter and a lexical fallback, and a FastAPI composition root in `main.py` serving only
  `GET /api/v1/health`; no use cases, database or migrations yet. Add them when implementing the
  project; document only commands that exist.
- The completed product runs through Compose, with synthetic data seeded into real storage and a
  main scenario that works without paid keys. An LLM lives behind a port with a deterministic fallback.
- Product screens consume real API responses. Missing endpoints show an honest error state.
  Test doubles belong in tests; synthetic seed data and fallback logic compute through real code.
- Every number has a method, sample size, date and evidence. Distinguish implemented, tested and
  verified on the stand. Fix evaluation plans before runs; publish negative results and limitations.
- Paid checks require an explicit manual request. Commands work or fail clearly naming the missing part.

## Work and memory

- An ordinary task may be done directly on its feature branch. Use `<type>/<slug>` without issue
  numbers or agent names. Reuse the user's chosen branch.
- Use GitHub Issues when the user requests tickets or an issue queue. See `.claude/tracker.md` for
  MCP, authenticated CLI and local-plan options. Missing GitHub credentials do not block local work.
- Parallel work requires explicit path ownership and agreed API, seed and token contracts. Each
  worker uses its own worktree. Shared files have one owner; avoid destructive Git operations in a
  tree another worker is using.
- Before stopping, update `context/SESSION.md` with current task, branch/SHA from Git, next actions,
  unresolved pitfalls and failed checks. Keep full working detail in `work/`; durable facts in `docs/`.
- `context/` has exactly three files, budgeted at 6000/6000/3000 characters. Run
  `python3 .claude/scripts/context_budget.py`. On overflow use `compact-context`; active user
  instructions are protected and may exceed the SESSION target with an explicit notice.
- Quick facts in `context/README.md` link to evidence and carry approved/implemented/verified status.
  Organizer answers go verbatim to `brief/QA.md`; unresolved assumptions stay in open questions.

## Commits and code

- Conventional Commits: `type(scope): subject`, English, imperative, lowercase subject, at most
  72 characters. Subject only: no body, trailers or issue numbers. One logical change per commit.
  Types: feat, fix, perf, refactor, test, docs, style, build, ci, chore, revert.
  Scopes: frontend, backend, api, ml, data, deck, video, social, readme, infra, deps; optional.
- Use the configured human Git identity. Preserve author configuration; setup may configure local
  hooks. Describe reasoning in product docs or the PR. PR titles follow commit format; issue closing
  references belong only in issue/PR text. Squash with an empty body.
- Agent names and generated-by signatures stay out of product files, commits and PRs. Models used
  by the product may be named as product dependencies. Internal tooling documents may name agents.
- Code and config identifiers, paths, logs and test names are English. Product copy uses dictionaries.
  Write code without comments/docstrings; explain non-obvious behavior in `docs/design-decisions.md`.
  Exceptions: shebangs and required suppression directives with a reason.
- Imports go at the top; dynamic imports are for lazy routes. Split files above 250 lines by
  responsibility. Use named modules rather than utils/helpers/common/misc dumping grounds.
- Agent instructions are English; product docs and slides use the jury's language. UI: RU and EN,
  RU by default. Product prose uses `humanizer` before release. Keep formatting edits separate.

## Skills and setup

- `skills/` is the source for both agents. `.claude/skills/<name>` and `.agents/skills/<name>` are
  relative symlinks. Resolve resources from the canonical source, not an alias. Catalog: `skills/README.md`.
- Frontend skill commands run in `frontend/`, defense commands in `presentation/`, unless specified.
  Repository paths are relative to its root; resources inside a skill are relative to that skill.
- Run `bash .claude/scripts/setup.sh` once per clone, before the first commit. It activates Git hooks
  and syncs aliases. After adding/removing/renaming skills, run `.claude/scripts/sync-agents.sh`.
- Manual skills are invoked explicitly; overlapping vendor workflows stay manual. Codex's policy
  metadata and Claude's frontmatter carry the same invocation choice. Load only relevant skills.
- For a library API, use current official docs through an available docs tool or primary sources.
  Configured optional plugins and MCP services are described in `.claude/settings.json` and `.mcp.json`.

## Submission and verification

- Use `submission` when submitting. `brief/`, `context/`, `work/`, `skills/`, agent files and paths in
  `.claude/scrub-paths` are removed. Product docs, including `docs/design-decisions.md`, are preserved.
  Team-only prose uses `<!-- scrub:start -->` and `<!-- scrub:end -->` blocks.
- `bash .claude/scripts/strip-ai.sh` previews cleanup on a temporary copy. `--apply` requires a
  committed tree, backs up files and checks safety before edits. `--apply --history` also rewrites
  commits to subjects only, fixes attribution and tags, removes internal paths and verifies blobs.
- `bash .claude/scripts/scrub-history.sh [source [output]]` uses the same engine to create a cleaned
  bare copy; source history stays unchanged. Review the copy before manually publishing it.
- Frontend verification: `cd frontend && npm run verify`. Deck: `cd presentation && npm run build`
  and `npm run speech:check`. Backend: `cd backend && uv run ruff check . && uv run mypy . &&
  uv run pytest tests/unit`, plus `uv run pytest tests/integration` for storage or stand changes.
  The pre-commit hook runs backend unit tests when `backend/` is staged.
- Verify the changed scenario, update its docs and inspect visible changes at 375px/1440px, both
  themes and languages when requested. Report which checks actually ran and remaining limitations.
