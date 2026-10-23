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

## Current state

- Task: brand and visual system for Brim, applied to the frontend shell.
- Branch and revision: `main` at `5a0777a`, all changes uncommitted (user handles git).
- Stand: frontend shell builds; `npm run verify` green (36 rules, 290 tests, build).

## How to continue

1. Wait for the user's feedback on the layer sweep and scramble animations (`frontend/src/shared/motion/`).
2. When the official case arrives, run `hack-kickoff`; recheck the tagline and README user line.
3. Brand rules: `docs/visual-system.md`; sources: `docs/brand/`; naming: `work/naming.md`.

## Pitfalls already hit

- Full-screen ring snapshots in View Transitions lagged; keep motion to transform/opacity.
- Percentage heights inside `aspect-ratio` grid tiles do not resolve; position images absolutely.
- `presentation` speech check reports slides changed after the brand-mark template update; run
  `npm run speech:sync` once the speech is written.

## Left, in order

1. User review of animations at 375/1440 in both themes.
2. Real product screens once the case is known.

## Red checks

- `cd presentation && npm run build`: deck builds, speech check reports 10 «slide changed since the
  speech was synced» errors (template speech).
