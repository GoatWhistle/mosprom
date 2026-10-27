# Design System: Brim

A dark workshop inside the slicer: data and telemetry hug the edges, the conversation sits in the
centre, and the only bright colour is the STE blue of the action in progress. Every screen must make
obvious which settings were chosen, why, and what the agent or printer is doing right now.

Accent and graphite come from STE Slicer 7.10 `resources/themes/material/theme.json`
(`primary`, `sidebar_header_bar`). Product-level rules: [visual-system.md](visual-system.md); brand sources: [brand/](brand/).

Values live only in `plugin/Brim/web/styles/tokens/`. This file names roles, usage and rules and
never copies a hex, px or ms value: change the token, not this file. The rules are enforced by
`plugin/tests/test_web_design_system.py`; run it with the plugin tests.

## 1. Overview

- **Register:** product UI, dense like a cockpit: 2–8px inside groups, 12–24px between blocks.
- **Layout:** the chat fills the window: sidebar, conversation, composer. Only the conversation
  column (`--chat-measure`), prose (`--prose-measure`) and single fields (`--field-max-width`) are
  capped.
- **Breakpoints:** 30, 48, 64, 75, 90 and 120rem (`max-width` uses the `.99` value). The narrow
  layout starts below 48rem: the sidebar becomes a drawer.
- **Motion:** every appearing element animates briefly and for a reason; panels also leave with
  an animation (`leave()` in `motion.js`). Switching chats dims the old thread while the project
  opens, then the new thread rises in with a stagger. Curves `--ease-*`,
  durations `--dur-*`, ready-made `--transition-*` and `--motion-*`. Reduced motion shrinks
  durations to 1ms and turns movement into a fade (`data-motion="fade"` on `html`).
- **Themes:** light and dark, chosen in the plugin settings. Components never know the theme: they
  read the semantic layer only. Theme change is the layer sweep; language change is the G-code
  text scramble (`motion.js`).

## 2. Colors

Components use semantic tokens only; palette tokens stay inside `tokens/`. Every semantic token
exists in both themes.

| Role | Token | Where |
|---|---|---|
| Page | `--surface-base` | body, timeline |
| Raised | `--surface-raised`, `--surface-raised-hover` | sidebar, cards, composer, drawer |
| Sunken | `--surface-sunken` | segmented track, stats, code |
| Selected | `--surface-selected` | current chat, segmented indicator, progress track |
| User | `--surface-user`, `--text-on-user` | the user's message |
| Washes | `--surface-accent-wash`, `--surface-danger-wash`, `--surface-scrim` | waiting state, failures, behind drawers |
| Text | `--text-primary`, `--text-secondary`, `--text-muted`, `--text-accent`, `--text-danger`, `--text-warning` | body, supporting, quiet, links, errors, risks |
| Accent | `--action-primary`, `--action-primary-text` | primary button, focus, running process, outer ring of the mark |
| Lines | `--border-subtle`, `--border-strong` | dividers, card edge, control outline |
| Status | `--status-success`, `--status-warning`, `--status-danger`, `--status-neutral` | dots and icons next to text |

Rules:

- The accent means one thing: action and the process in progress. It never decorates.
- Text on the blue button is white in both themes; hover and press get darker.
- Status is an icon plus text; colour only reinforces it.
- Contrast is checked by `test_theme_contrast`: text 4.5:1 on every surface, focus, accent and
  status marks 3:1, in both themes.

## 3. Typography

- **Sans:** `--font-sans`, Onest, for everything that is read.
- **Display:** `--font-display`, Handjet, for printer numbers only (print time, mass) at
  `--font-size-display`.
- **Mono:** `--font-mono` for paths, G-code, setting keys and external tool identifiers; never for
  Cyrillic prose, card eyebrows or translated tool names.
- **Optical centre:** text in pill controls is lifted by `--optical-lift` (fields by twice that):
  Onest's lowercase sits about a pixel below the geometric centre of the line.
- **Scale:** `--font-size-caption`, `-label`, `-body-sm`, `-body`, `-subheading`, `-heading`,
  `-display`, each with its `--line-height-*`. No other sizes.
- **Weights:** `--weight-regular` for text, `--weight-medium` for controls and headings.
- **Telemetry:** the `.telemetry` class is the only place for upper case.
- **Numbers:** tabular (`--font-numeric`) wherever values line up.

## 4. Elevation and shape

- **Grid:** 4px. Every line height is a whole multiple of 4 (`--line-height-*` are px), so dots,
  icons and text land on whole pixels.
- **Control heights:** three only: `--control-height-mini` (28), `--control-height-compact` (36),
  `--control-height` (44). A segmented control, a field and a button in one row are the same height.
- **Shapes, three tiers:** panels and cards are sharp (`--radius-lg`, 0); single-line controls are
  pills (`--radius-pill`: buttons, fields, segmented controls, chips, switches, dots); multi-line
  text surfaces are softly rounded (`--radius-md`: composer, user message, chat row). Inline code
  uses `--radius-sm`.
- **Lines before shadows:** a card is `--surface-raised` with a hairline `--border-subtle`.
  `--shadow-ring` outlines secondary controls, `--shadow-raised` lifts the segmented indicator,
  `--shadow-float` is only for drawers and the floating jump button.
- **Layers:** `--layer-*` only.
- **Targets:** every control is at least `--target-min` tall through its `::before` hit area, even
  when the visible control is compact.

## 5. Components

Plain CSS classes in `styles/components/`, chat layout in `styles/chat/`. A screen never writes its
own variant of an existing component.

- **Button:** `.button` is primary; `.button-secondary` for the rest, `.button-ghost` inside
  toolbars, `.button-danger` for destructive choices. `.button-compact` inside cards and lists.
  One primary per area: sidebar has New chat, a confirmation card has Apply.
- **Icon button:** `.icon-button`, `.icon-button-primary` for Send. Icons come from `icons.js`.
- **Segmented:** `segmented.js` with a sliding indicator, radio semantics and arrow keys; used for
  mode, language and theme. The selected option is a raised `--surface-indicator` pill with accent
  text, so the choice is obvious in both themes.
- **Card:** `.card` with `.card-eyebrow` (or `.card-header` when the card has its own action),
  `.card-text`, `.card-actions`; `.card-active` while the agent waits for the user, `.card-danger`
  for failures. Instructions do not live in cards: while a question or confirmation is active, the
  composer placeholder says what to type.
- **Field:** `.field`, `.field-label`, `.field-input`; `.select` for the compact skill picker.
  Required fields get a small red `.field-required` star; optional fields get no mark. No example
  text under fields: a placeholder carries the format.
- **Switch:** `.switch` with `role="switch"` for on/off settings such as an MCP server.
- **Settings:** a right drawer of sections; each section is a heading and one panel. Values that
  apply instantly (language, theme) have no Save; Save is enabled only when something changed.
- **Chip:** `.chip` with the file type in `.chip-ext`.
- **Brand:** `brand.js` builds the mark, wordmark and lockup from one set of paths; the spinner is
  the looping mark. The agent's messages carry the static mark instead of a coloured stripe.
- **Thread:** the agent's side of the conversation sits in one column (`--agent-indent`): its mark
  appears once per run of agent entries, tools and cards align with the text.
- **Quick start:** an empty chat offers four scenario cards (`.suggestion`); a click fills the
  composer, it never sends on its own. A question with a single set of options answers in one click.
- **Splash:** until the first view arrives a full-screen splash shows the looping mark and the
  connection state; a missing token is an error splash, not an empty interface.
- **Tag:** `.tag` is a small sunken pill for counts, steps, server names and tool totals.
- **Sidebar rail:** on desktop the sidebar collapses to `--sidebar-rail` with the toggle at its foot;
  icons keep their position while the width animates and labels fade, the state is remembered per
  browser. Below 48rem the sidebar stays a drawer.
- **Chat list:** one line per chat (title, time on the right), grouped by day; the selection is one
  `.chat-indicator` that slides to the clicked row at once, before the plugin answers.
- **Header meta:** agent state (dot or looping mark) and save state (icon) as separate items.
- **States:** `.empty-state`, `.banner` (neutral, `-accent`, `-danger`), `.status-dot`,
  `.progress` (determinate scale or indeterminate travel), `.travel` dashed nozzle line for a
  running tool.

## 6. Do's and Don'ts

### Do:

- Take every value from a token and every text from the plugin dictionaries.
- Give every state a designed look: loading, empty, waiting, error, offline.
- Check 375 and 1440 in both themes and both languages before calling a screen done.

### Don't:

- No gradients, glows, glass or gradient text; no emoji in the interface.
- No hover styles outside `(hover: hover) and (pointer: fine)`.
- No coloured side stripes on cards, rows or messages.
- No caps-lock labels outside `.telemetry`; no fake numbering.
- No dash or middle dot as a separator: split values into separate items, tags or columns.
- No colour as the only signal of state; no text below 4.5:1 in either theme.
- No typing the name in a font: use `brand.js` or the SVG files.
- No blue for decoration, headings or charts that do not mean action or a running process.
