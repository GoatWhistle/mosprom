# Session state

Updated: 2026-10-23, MSK

## Explicit user instructions

- 2026-10-23: «нормальный кейс узнаем чуть позже» — the final organizer case is not published yet;
  the preliminary brief is an MCP server with chat over a slicer for FDM 3D/5D printing (STL + photo +
  text → parameters and G-code, remote printer fleet control).
- 2026-10-23: «названия на английком все»; the mark stands next to the name, never inside it; the
  name is self-sufficient with and without the mark; logo must be animated and static.
- 2026-10-23: name chosen «брим» (Brim), accent «Раскалённый пластик».
- 2026-10-23: visual system file in docs with spacing, colours, fonts, logo usage, variations, visual
  elements and jokes; frontend redesign, favicons, README; all animations thought through.
- 2026-10-23: theme switch «Печать слоями», language switch «Расшифровка»; previous wave/burst and
  print-sweep versions were rejected as laggy and ugly.


- 2026-10-23: «ТЗ лежит в папке task, также там лежит транскрибация видео. изучи. ну и все , дальше как по репозиториюб по правилам все раскидай и уже потом будем обсуждать кейс»
- 2026-10-23: «https://665dc1hack2026.k8s.stereotech.cloud/ вот тут еще данные»

- 2026-10-23: «так, все тз раскидай по файлам чтобы оно было и запушь в репо все это дело»

- 2026-10-23: «нет. я тебе говорю пуш в мейн сразу эт»

- 2026-10-23: «на видео забей, удали вообще»
- 2026-10-23: «только транскрибация пусть летит»

- 2026-10-23: «а теперь давай подумаем как это можно реализовать»
- 2026-10-23: Windows test host question answered «Пока только macOS/Linux».

- 2026-10-23: «стой»
- 2026-10-23: «удали все скиллы, которые тебя щас путают. ты сликшом галлюционируешь»

- 2026-10-23: «мы пока в read-only режиме, потом пропишем это в план и реализуем.»
- 2026-10-23: «все по чистой архе пишем, сделай аадаптер подключения к LLM по OpenAI-совместимый API.»
- 2026-10-23: «геометрию агент должен получать числами, а «просмотр» сцены нужен как структурированное состояние. Рендер картинкой идёт только как дополнение.»
- 2026-10-23: «ну мы это все всегда будем хранить в БД очевидно»; «нет, постгрес»; «компоуз очевидно.»
- 2026-10-23: «Плагин должен интегрировать в интерфейс программы окно встроеного чат-бота.»
- 2026-10-23: «все удаляй нахуй папочку фронтенда братишка, мы без него» — authorizes frontend removal and its dependent configuration cleanup; product implementation remains pending.

- 2026-10-23: «сгенерь и пропиши в .env.example» — explicitly requests a generated connection token in the tracked example file.

## Current state

- Task: discussing plugin loading and runtime. User chose a VM: «поднимать все буду на виртуалке». Preserve concurrent backend/plugin implementation. Target runtime has not been tested.
- Branch: main; HEAD 28cc4017b0782fb56430fabc3238ad59620943e6. No commit or push in this turn. Prior uncommitted skill removals/instruction edits preserved.
- Approved design, not implemented: embedded STE Slicer chat; Clean Architecture; OpenAI-compatible LLM adapter; PostgreSQL in Compose for persistent conversations and results.
- Agent interviews the user with a question pool and follows up on missing/ambiguous answers. Model knowledge, slicer facts and user answers only for now; no reference database or web search.
- Code supplies initial facts, structured scene updates and numerical geometry. Agent chooses print settings, transformations and tool calls. Image renders are supplementary.
- Attachments stay in the conversation until the agent imports them. Every successful slice automatically saves matching G-code and 3MF. Improvements need a new user request; the agent may repair execution errors within the agreed requirements.
- Auto applies edits autonomously; Ask before edits requires approval before applying a related group of edits. Enforcement belongs to code. Both modes interview the user.
- Approved: agent in backend Compose service, PostgreSQL separately in Compose; plugin executes slicer tools and provides embedded chat. Backend address configurable, default localhost. Implementation plan delivered in chat; code remains a template.
- Prior work removed five project skills: hack-kickoff, codebase-design, domain-modeling, docs-writing, writing-for-agents. Their aliases/dependent invocation edits remain uncommitted. No global skills changed.
- PDF embedded-chat wording and website browser-SPA wording conflict. User chose embedded chat; official sources remain unchanged. WebView support is unverified.

## How to continue

1. Continue design discussion; do not implement the agent, database or plugin until authorized.
2. Implement the agreed plan only when requested; verify Qt integration against the supplied STE Slicer. Read brief/requirements.md and TECHNICAL.md without silently restoring a browser frontend.
3. User chose a VM for the slicer stand; installation and runtime validation remain pending. Check checkpoint slots and submission fields when needed.
4. Preserve Brim name and molten-plastic brand in docs/visual-system.md and docs/brand/.

## Verification and limitations

- Checks passed: frontend absent, Compose config valid/backend only, bake print/backend only, git diff --check, context budgets, changed docs links (excluding root README).
- Presentation build passed after npm ci --ignore-scripts fixed missing qrcode. speech:check still reports the ten known stale sections; root README link check still fails on pre-existing missing docs/images/hero.png. No container startup or image build run.
- Previous intake: PDF pp. 1–12, transcript, website task and seven DOCX tasks read; seven JPGs viewed. Original hashes, ZIP CRC and STL sizes checked; no slicing or physical validation.
- Video files deleted at user request, transcript retained. Website key excluded from repository.
- Historical/template docs and reusable web skills may mention the removed frontend; they are not the current product architecture.

## 2026-10-23 backend implementation (agent plan)

- User: «так плагин я отдельно буду писать» — plugin work stopped; user writes it. `plugin/Brim/` holds an unfinished, unverified draft (protocol, ledger, geometry, slicer modules written from STE Slicer sources, no UI/extension/tests); do not treat it as done.
- Backend done in working tree, not committed: PostgreSQL repositories, dbmate migration, OpenAI-compatible adapter, agent loop, HTTP and WebSocket API, Compose db/migrate/backend. Contract: `work/protocol-contract.md`; tool schema source `backend/src/app/domain/tools.json` (frame only `scene`).
- Checks run: ruff, mypy strict, 77 pytest tests (11 repository + 7 e2e on real PostgreSQL via docker, scripted LLM, fake plugin over WebSocket); Compose up with data kept after down/up. Not run: real LLM, real slicer, Windows.
- Artifact chunk `sha256` is the digest of the whole artifact (same on every chunk).
- `.env.example` had an uncommitted token-like BRIM_CONNECTION_TOKEN value; blanked and removed.
- Next: commit, update docs/ (api, architecture, running) and ADR for PostgreSQL, hand the contract to the plugin author.
