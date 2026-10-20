---
name: "{{PRODUCT}}"
description: "{{One-line visual direction, e.g. calm workspace where data is the main visual}}"
---

# Design System: {{PRODUCT}}

{{Two sentences: the visual idea and the one thing every screen must make obvious.}}

Source style, picked by the user: {{https://styles.refero.design/style/<uuid>}}, extracted from
{{source site URL}}. Full extraction and conflicts resolved with the user: `work/design/style.md`.

Values live only in `src/shared/styles/tokens/`. This file names roles, usage and rules and never
copies a hex, px or ms value: change the token, not this file. `npm run tokens:export -- --print`
shows the current values. Until the brand is chosen the tokens hold a neutral placeholder palette,
Inter and JetBrains Mono.

## 1. Overview

- **Register:** product UI. {{Density: calm, standard or dense, and why for these users.}}
- **Layout:** the site uses the full screen width. Pages have no `max-width`; padding is
  `--space-page` and `--space-page-wide` from 75rem. Width is filled by panels: sidebar, list with
  detail, filters with results. Grids use `minmax()` and `fr`. Only prose (`--prose-measure`) and a
  single field (`--field-max-width`) are capped.
- **Breakpoints:** 30, 48, 64, 75, 90 and 120rem, the same values in `matchMedia`.
- **Motion:** every appearing and collapsing element animates, briefly and with a reason. Tokens:
  curves `--ease-*`, durations `--dur-*`, entrances `--motion-*`. Reduced motion shrinks durations
  to 1ms and turns movement into a short fade.
- **Themes:** light and dark only, no system option in the switch; the system theme until the
  user picks, applied before first paint. Components never know
  the theme: they read the semantic layer only.

## 2. Colors

Components use semantic tokens only; palette tokens (`--neutral-*`, `--accent-*` and the like) stay
inside `tokens/`. Every semantic token exists in both themes.

| Role | Token | Meaning | Where |
|---|---|---|---|
| Page | `--surface-base` | background of the app | body, page |
| Raised | `--surface-raised`, `--surface-raised-hover` | content on top of the page | cards, panels |
| Sunken | `--surface-sunken` | recessed track | segmented track, wells |
| Selected | `--surface-selected` | current choice inside a track | segment indicator |
| Text | `--text-primary`, `--text-secondary`, `--text-muted` | body, supporting, quiet | headings and body, hints, placeholders |
| Accent | `--action-primary`, `--action-primary-text` | {{what the accent means: action, selection, link}} | primary button, links, focus |
| Lines | `--border-subtle`, `--border-strong` | separation, control outline | dividers, card edge, secondary button |
| Focus | `--focus-ring` | keyboard position | the shared `:focus-visible` |
| Status | `--status-success`, `--status-warning`, `--status-danger` | {{confirmed, needs a human, failed}} | status icons with text |

Rules:

- The accent means one thing: {{action and selection}}. It never decorates.
- Status is an icon plus text, colour only reinforces it.
- Contrast is checked by `npm run rules` (`contrast`): text 4.5:1 and the focus ring 3:1 on every
  surface, in both themes.
- {{Brand rule, e.g. "warm colour only for what needs a human decision".}}

## 3. Typography

- **Sans:** `--font-sans`, {{brand font, loaded locally from `@fontsource-variable/*`}}.
- **Mono:** `--font-mono` for codes, identifiers and paths, never for prose.
- **Scale:** `--font-size-caption`, `-label`, `-body-sm`, `-body`, `-subheading`, `-heading`,
  `-heading-lg` (fluid page title). Each has a matching `--line-height-*`. No other sizes.
- **Weights:** `--weight-regular` text, `--weight-medium` controls, `--weight-semibold` headings.
- **Numbers:** tabular (`--font-numeric`) wherever values line up; formatted with `Intl` by locale.
- Page title is `PageHeader`, card titles are `Card title`; screens write no `h2`-`h6` by hand.

## 4. Elevation

- **Radii:** `--radius-sm` small marks, `--radius-md` controls, `--radius-lg` cards and tracks,
  `--radius-pill` pills and scrollbar thumbs. Nested corners stay concentric.
- **Lines before shadows:** a card is `--surface-raised` with a `--border-subtle` hairline.
  `--shadow-ring` outlines secondary controls, `--shadow-raised` lifts the selected segment,
  `--shadow-float` is reserved for popovers and dialogs.
- **Layers:** `--layer-*` only, from `--layer-raised` to `--layer-skip-link`.

## 5. Components

Everything is built from `src/shared/ui`; a screen never writes its own variant of an existing
primitive.

- **Button / ButtonLink:** `primary` for the one main action on a screen, `secondary` for the rest,
  `ghost` inside cards and toolbars. Pending keeps the width and sets `aria-busy`.
- **Card:** `title`, `eyebrow`, `description`, `actions`; `motionIndex` staggers the first load.
- **Segmented:** two to four mutually exclusive options; `display="icon"` and `"short"` keep the
  full name for screen readers.
- **States:** `Skeleton` after 200ms and held 300ms, `Spinner` after 400ms, `stale` dimming when
  data is already shown, `EmptyState` with a 48px icon, `ErrorState` with retry. `NoValue` replaces
  manual dashes.
- **Data components:** {{the product's signature data component: what it shows, which tokens it
  uses, how it reads at 375px. Add it to `shared/ui/data-display` or `entities/`.}}
- **Motion per element:** press scales to `--press-scale`; content swaps through `Swap`;
  overlays fade and scale from 0.95 at the anchor and close faster than they open; screen changes
  use View Transitions. Values: `src/shared/styles/tokens/motion.css` and `keyframes.css`.

## 6. Do's and Don'ts

### Do:

- Fill the width with panels and data; let one primary action lead each screen.
- Take every value from a token and every text from the dictionaries.
- Give every state a designed look: loading, empty, error, stale, offline.
- Check 375, 1440 and 1920 in both themes and both languages before calling a screen done.

### Don't:

- No gradients, glows, glass or gradient text; no emoji in the interface.
- No narrow centred column, no `max-width` on pages.
- No grids of identical icon cards, no KPI tiles without a conclusion.
- No caps-lock section labels, no fake 01/02/03 numbering, no coloured side stripe on cards.
- No dash or middle dot as a separator; no `null` or "Loading..." text instead of a skeleton.
- No colour as the only signal of state; no text below 4.5:1 in either theme.
- {{Product-specific don't.}}
