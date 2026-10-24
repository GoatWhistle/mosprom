# Session state

Updated: 2026-10-24, MSK

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

- 2026-10-23: «Implement the plan.» — authorizes implementation; supersedes the earlier read-only phase.
- 2026-10-23: «продолжи проверять».
- 2026-10-23: «ты там все нормально делаешь? или ты уже делаешь что-то ненужное?» — finish scoped verification; no new features.

- 2026-10-23: «все то, что ты сделал закоммить и пушь. вот вообще все изменения».

- 2026-10-23: «нужно чтобы каждый новый чат был подвязан к одному рабочему пространству (файлу) чтоли, как то так брат ; нужно чтобы я мог менять чаты и как бы из за этого менялись файлы . понял задачу?»
- 2026-10-23: «план именно задачи для исправления чатика сделай братан».
- 2026-10-23: plan `misty-honking-crescent.md` (agent in plugin as OpenAI client + MCP host; backend
  only a Claude proxy) referenced for implementation.
- 2026-10-23: «продолжи без тестов, можешь их больше не писать».
- 2026-10-24: «задеплой 0.3.0 на виртуалку и прогони сценарий».
- 2026-10-24: consultation transcript pasted (beginner chat bot; photo of printed part → defects →
  parameter changes; calibration test parts); «Я бы сделал типа скилов: калибровка-новичок … продвинутый
  инженер …»; «+ тогда нужна выгрузка переписки»; PNG «да, оба варината»; plan misty-wishing-hummingbird
  approved with «делай».
- 2026-10-23: «Давай попробуем оба варината в разных ветках и я выберу который понравится
  и учитывай это ~/.claude/plans/spicy-tinkering-floyd.md» — plan updated with embedding notes.

- 2026-10-24: «Давай подумаем над скилами и добавим в базовые тулы работу с docx, xlsx, csv крч с
  файлами чтобы агент их мог прочесть нормально»; skills: novice, engineer, material, defects;
  agent picks + manual pin; formats DOCX/XLSX/CSV/TXT/MD/JSON/PDF.

- 2026-10-24: «твоя задача запустить новый бэк из main ветки и там новые изменения вроде уже лежат на вм,
  но ты все равно перевроверь ты должен создать 7 чатов и через brim всё прогнать и сохранить, также сам
  перепроверяй качество, все найденные баги фиксируй в md»
- 2026-10-24: «надо переделать 2 чата зановго и через brim всё прогнать и сохранить, также сам перепроверяй
  качество, все найденные баги фиксируй в md»; gear STL «скачай заного из ТЗ заказчика … пусть папка соотвествует».

## Current state

- Worktree `../mosprom-hack-spa`, branch `feat/browser-spa` from main b7fdbc0 (2026-10-24): browser SPA per
  website §3.2 next to the QML panel. `plugin/Brim/browser/` (loopback HTTP, token, long-poll view,
  whitelisted actions on Qt thread, upload/download) and `plugin/Brim/web/` (vanilla ES modules); menu
  «Открыть в браузере»; plugin 0.5.0. Verified only on Linux with real presenter on fakes + headless
  Chromium; not run in STE Slicer. Not merged, not pushed. Rationale: docs/design-decisions.md.
- Stand 2026-10-24 16:40–17:00: deployed 0.5.2 = uncommitted merge of feat/calibration-figure + feat/browser-spa
  (0.5.1 backup %TEMP%\Brim-0.5.1-backup). Edge via menu passed: STL upload in file dialog (1.2 MB), answer to
  question card, auto run (transform, settings, slice 0 h 53 min, 3.3 g), result card, G-code download, recover
  button. Stand scripts must be UTF-8 with BOM (PS 5); a mojibake chat title was fixed in chat.json
  (backup chat.json.bak-mojibake). Old tab after slicer restart says "no connection" forever (new port).

- Branch `fix/jury-run-findings` from main 4c085cd, not pushed: plugin 0.4.1 with run fixes (overrides reset
  on empty chat, extruder-ordered slice report, `set_object_extruder`, 5D rotation-axis data and rules,
  chat.json replace retry, wait for STE error check before slicing, engine_log and hung-slice stop,
  45-min slice limit). Bugs and run table: [work/jury-run-bugs.md](../work/jury-run-bugs.md).
- Stand: backend `brim-backend:latest` rebuilt from main 4c085cd (always opus), compose override in
  session scratchpad; plugin 0.4.1 deployed (0.4.0 backup %TEMP%\Brim-0.4.0-backup). Task BrimSlicer now
  starts in the STE folder (OpenSCAD for 5D); 5D licence activated 2026-10-24 (10 days). Task BrimType runs
  %TEMP%\steps.ps1 (click/text/key/sleep lines from brim-steps.txt).
- Seven models run and exported to stand `Desktop\results\<model>\`; copy `~/mosprom-results/2026-10-24/`.
  Gear (now `results\Шестерня`) and figurine rerun clean, now on main (B20 prompt rule,
  deployed to stand as single file); old exports in stand `Desktop\results-old-2026-10-24`, local `_old/`. Older history: work/session-log.md.

## Verification and next actions

- Plugin unit tests 155 passed, 2 skipped (3.14) after each fix; fixes verified on the stand as listed in
  the bugs file. Python 3.5 run not repeated. No new tests (user instruction).
- Open: B6, B14–B19 in the bugs file; ZIP size limit unknown (figurine G-code 298 MB, Wilo 201 MB).
  `fix/rerun-gear-figurine` merged into main (fast-forward); main not pushed.
