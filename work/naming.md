# Naming

Status: draft, 2026-10-23. The final case is not published yet; names are based on the preliminary
brief (MCP server with chat over a slicer: STL + photo + text → FDM 3D/5D parameters and G-code,
remote printer fleet control). Visual direction: Refero style "Max Yinger"
(https://styles.refero.design/style/a7891223-a93e-4731-a1aa-4079f1ee928b).

Preview page: https://claude.ai/artifact/FSXPr7HhjCipD7EDTrdzTP, local copy `work/design/names.html`.

Update 2026-10-23: user asked for English names only, more concepts, a mark placed next to the
name (never inside it), each name self-sufficient, animated and static versions, favicon.
Current set of 12, scored: Facet 22, Brim 22, Nonius 21, Ferma 20, Gyroid 20, Seam 20, Spool 19,
Lamina 19, Retract 18, Datum 18, Z0 17, Quinta 16. Shortlist: Facet, Brim, Nonius.
Known uses for new names: Seam — Fraunhofer IWU SEAM high-speed AM process; Spool — Spoolman,
Spoolstock, Spool Log filament trackers; Datum — Datum3D design firm, Datum blockchain; Facet,
Brim, Retract — no product found (Retr3d open project).

## Inputs

- Mechanism: tune slicer parameters until they fit the model, then emit G-code.
- Domain terms: layer, nozzle, infill, gyroid, retract, brim, first layer, Z-offset, G28, M600, print farm.
- User: novice operator and a print-farm technologist.
- Feeling after: "the settings just fit".

## Candidates by route

| Route | Candidates |
|---|---|
| Procedure | Brim, Prime, Retrakt, Infill, Purge (dropped), Homing |
| Mechanism metaphor | Ply, Weft, Bead, Strata, Vitok, Ostov |
| Instrument | Nonius, Caliper, Gauge, Datum, Shim, Micron |
| Coined | Filo, Layra, Plyx, Gyra, Extrudo, Kalibra |
| Verb | Slice, Dial, Feed, Stack, Extrude |
| Outcome / code | Z0, G28, M600, Lamina, Kvinta, Ferma, Gyroid |

Dropped: Sloy (Sloyd, AI 3D generation for printing), Kalibr (missile), Purge (negative), Benchy
(trademark), Loom (big brand).

## Scored shortlist

| Name | Story | Say once | Mark 16px | Distinct | Pitch | Σ | Known uses |
|---|---|---|---|---|---|---|---|
| Нониус / nonius | 5 | 4 | 5 | 3 | 4 | 21 | Nonius hotel IPTV (PT), Enraf-Nonius medical; none in 3D printing |
| Ферма / ferma | 4 | 5 | 4 | 3 | 4 | 20 | No print product found; generic word |
| Гироид / gyroid | 4 | 4 | 5 | 3 | 4 | 20 | GyroidVault (open-source model manager); generic term |
| Ламина / lamina | 4 | 5 | 4 | 2 | 4 | 19 | Lamina, concrete 3D printing software (UNSW spinout); Lamina3d CNC nesting |
| Z0 | 4 | 3 | 5 | 3 | 3 | 18 | Not checked |
| Квинта / kvinta | 4 | 3 | 4 | 2 | 3 | 16 | Quinta, 5-axis CNC startup (UC Irvine) |

Searches: web, 2026-10-23. GitHub, npm, domains and trademarks not checked yet.

## Finalists

1. **Нониус** — the mark explains the mechanism: picking a parameter value is the moment two
   scales align. Engineering jury recognises the instrument; a real caliper works as a stage prop.
2. **Ферма** — if the final case centres on fleet management: print farm + structural truss.

## Taglines

- Параметры, которые сошлись.
- Настройка до десятой миллиметра.
- Слайсер подбирает. Вы печатаете.
- Первый слой — с первого раза.
- Парк принтеров, который держит нагрузку.
- Главное — внутри.

## Recommended: Нониус

- Origin: «Название — от нониуса: шкалы штангенциркуля, по которой читают десятые доли миллиметра».
- Typographic device: a vernier tick scale under the wordmark; one tick in the accent colour marks
  the aligned value.
- Pitch: «Знакомьтесь, Нониус — надстройка над слайсером, которая подбирает параметры печати по
  модели, фото и запросу и сразу отдаёт G-код».

Decision 2026-10-23: user picked **Brim**, accent "hot plastic" (`#ff8a3d`), tagline «Держит с первого слоя» / "Holds from the first layer". Rationale: brim holds the part on the bed from the first layer; the product holds the slicer settings. Brand sources: `docs/brand/`, rules: `docs/visual-system.md`.
