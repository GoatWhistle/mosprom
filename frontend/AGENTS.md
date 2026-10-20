# Frontend rules

These rules override any skill's recommendations. If a skill says otherwise, this file wins.
The repo-wide rules in the [root `AGENTS.md`](../AGENTS.md) apply here too.

The visual system is set on day one from a style the user picks on <https://styles.refero.design/>
(skill `refero-style`); the agent never picks a style itself. The result lives in `PRODUCT.md` and
`DESIGN.md` next to this file and as values only in `src/shared/styles/tokens/`. Until then the tokens
hold neutral placeholders; nothing below depends on them.

## Skills

The skills below live in the shared root [`skills/`](../skills/) directory. Both agents discover
that same source through their root skill symlinks; catalog: [`skills/README.md`](../skills/README.md).

- Any UI work (screens, components, layout, UX, a11y) goes through `impeccable` and `ui-ux-pro-max`.
  Take structure and UX/a11y checks from `ui-ux-pro-max`, never its ready-made palettes, fonts or
  stack advice (it may suggest Tailwind or shadcn; section 2 wins). `frontend-design` sets the
  aesthetic bar for new surfaces.
- `impeccable` runs its launcher `scripts/impeccable context` once per session (downloads its engine
  on first run, needs network once). Its live detector hooks are machine-local: run
  `/impeccable hooks on` once per machine.
- Motion:
  - `animate` — builds a new animation, deciding in the right order: whether, purpose, tool,
    properties, curve, interruption, exit;
  - `emil-design-eng` — polish and motion philosophy, tie-breaker for disputed calls;
  - `review-animations` with its `STANDARDS.md` — mandatory before shipping any feature with motion;
    it is user-invoked only, so read `review-animations/SKILL.md` and `STANDARDS.md` directly and apply
    them;
  - `improve-animations` — audit and improvement plan;
  - `find-animation-opportunities` — where motion is missing;
  - `animation-vocabulary` — the name of an effect.
- `break-ui` — worst-case data (long names, empty, huge counts, non-Latin, extreme numbers) against a
  screen before it is called done.
- `frontend-audit` — the five audits before final polish.
- `PRODUCT.md` and `DESIGN.md` are the context `impeccable` loads: a short product brief and the
  meaning of the tokens. Write them by hand or with `impeccable init`; keep values only in tokens.
- Promo video and motion for the pitch belong to `presentation/` and the `hyperframes` plugin, not to
  the app.

## 1. Hard limits

- A `.ts/.tsx/.css/.html` file is at most 250 lines. Split long files by responsibility, not
  mechanically.
- No comments in code at all: no line, block, JSDoc, nor in CSS, HTML or configs. Exceptions:
  `// biome-ignore <rule>: <reason>`, `@ts-expect-error <reason>` and a shebang. Explain the
  non-obvious in `docs/` (usually `docs/design-decisions.md`), never in code.
- Generated files (`schema.gen.ts` from OpenAPI) are exempt from line and comment limits.
- At most 20 source files per folder. Folders named `utils`, `helpers`, `common`, `lib`, `misc`,
  `core` are forbidden.
- No import cycles. All imports at the top of the file; dynamic `import()` only for lazy routes.
  Named exports only; default export only where a tool requires it.
- Identifiers, file names, dictionary keys, logs and errors are in English. Cyrillic lives only in
  `src/shared/i18n/locales/ru/`.

## 2. Stack

- React 19, Vite, TypeScript, react-router 7. API client is `openapi-fetch`; types are generated from
  the backend OpenAPI (`npm run api:types`) and never written by hand.
- Every API request goes through TanStack Query: cache, retry, invalidation after mutations. `fetch`
  inside `useEffect` in features is forbidden.
- No mocks. Every screen shows only data the running backend returned through `shared/api`. No mock
  files, `__mocks__`, fixtures or hardcoded domain arrays in `src/`, no MSW, json-server or faker,
  no `VITE_USE_MOCKS` switches, no `queryFn` or `initialData` with literal data. A missing endpoint
  means the screen shows its error state and the endpoint is requested from the backend stream.
  Test doubles live only in `tests/`. Check `no-mocks`.
- Texts — `i18next` and `react-i18next`; classes — `clsx`; icons — `lucide-react` plus our own set.
- Linter — Biome: indent 2, width 100, double quotes, no semicolons, LF. Enabled: `noDefaultExport`,
  `noExplicitAny`, `noNonNullAssertion`, `useImportType`, `noConsole` (except error/warn), cognitive
  complexity at most 15.
- TS strict with `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes` and `verbatimModuleSyntax`.
  Alias `@/`.
- Tests: Vitest (`tests/` mirrors `src/`), e2e on Playwright with axe.
- No UI kits (shadcn, Radix, MUI, Tailwind) and no animation libraries. Our primitives are built on
  CSS, WAAPI and View Transitions.
- `npm run verify` runs `rules && typecheck && lint && test && build`. A feature is done when it is
  green.

## 3. Structure (FSD)

```text
src/
  app/        providers, router with lazy routes, root layout (header, skip link, route focus), route fallback, root error
  pages/      a screen = composition of features and slots, no own logic
  features/   user scenarios
  entities/   data and its display, *.queries.ts
  shared/
    api/      openapi-fetch client, schema.gen.ts, ApiError (status, code, kind), query client
    ui/       primitives grouped: data-display, forms, layout, overlays, primitives, states
    motion/   motion primitives
    i18n/     locales/{ru,en}/<ns>.json, resources.ts, LocaleProvider, useTranslation, formatters, error keys
    theme/    ThemeProvider, useTheme; light or dark, the system theme until the user picks one
    hooks/    use-media-query (use-stored-flag, use-online when a screen needs them)
    styles/   global.css, reset.css, compose.module.css, tokens/*
```

- Imports go only downward: `app → pages → features → entities → shared`. Siblings within a layer do
  not import each other; features are wired through props and slots on the page.
- A component lives in a `kebab-case/` folder with `name.tsx` and `name.module.css`. Every feature and
  entity has an `index.ts` with named exports. Hooks are named `use-xxx.ts`.
- Props are a `readonly XxxProps` interface; variants are a `Record<Variant, string>` map.
- A repeated block becomes a component in `shared/ui` or `entities`; never copy markup. A new screen is
  built from the same primitives as its neighbours. A home-made analogue of an existing primitive is
  forbidden.
- The backend owns logic and permissions. Hidden data simply never reaches the frontend; the frontend
  does not decide what to hide.

## 4. Texts and languages

- Tab titles: `Page | Product` on every page, `Product | tagline` on the home page, built only by
  `documentTitle` in `src/shared/i18n/document-title.ts` (the one place `|` is allowed). Every page
  in `src/pages/` calls `useDocumentTitle`; check `page-titles`. Favicons, app icons, the manifest
  and the social cards are generated by `npm run brand:assets` from the mark and the tokens and are
  never edited by hand: skill `site-identity`.
- Two languages, RU by default and EN. Every UI string comes only from
  `shared/i18n/locales/{ru,en}/<ns>.json`, namespaced per feature plus `common`/`errors`.
- Keys are always full `ns:path`, in English. `resources.ts` uses `satisfies`, key types are inferred
  from `en`, so a typo in a key breaks typecheck. A test asserts that ru and en have the same key set.
- Import `useTranslation` from `@/shared/i18n`, never from `react-i18next`: the wrapper loads every
  namespace so full keys typecheck.
- `LocaleProvider` takes the saved choice from `localStorage` (inside try/catch), then
  `navigator.languages`, otherwise ru. It sets `<html lang>` and the document title.
- Literal text is forbidden in JSX, `aria-label`, `title` and `placeholder`. Expected text in tests
  also comes from the dictionary.
- Numbers, percentages, dates and money are formatted with `Intl` per locale; in messages use
  `{{x, number}}`. Never concatenate strings out of numbers.
- The data model stores no phrases. Statuses render through `Record<Status, MessageKey>`.
- Errors render by key `errors:api.<code>`, falling back to `errors:kind.<kind>`. The backend
  `message` field never reaches the UI.
- No em dashes anywhere in UI text, not even inside a sentence, and no middle dots or pipes as
  separators: "A · B", "x — y" read as AI output. Rephrase with a colon, a comma or a new sentence;
  show several attributes as separate elements with an icon and `gap`. A short `–` is allowed only
  in numeric ranges.
- No characters that imitate icons: arrows (→ ← ⇒ ➜), checks and crosses (✓ ✔ ✗ ✕), pointer
  triangles (▶ ▸). Use `Icon` (`arrow-right`, `check`, `x`, `chevron-right`) or `StatusBadge`. Skill
  `asset-sources`.
- The EN version is fully English. Assets with text exist in two versions, `.ru.svg` and `.en.svg`.
- Backend data (LLM output, user content) is not translated and is rendered with its own `lang`.

## 5. Motion

Everything is animated, including opening and closing of everything that pops up or expands. Every
element type has a defined behaviour.

- Animate only `transform`, `opacity`, `clip-path` and `filter: blur` up to 2px. Forbidden: animating
  `width`/`height`, `transition: all`, `ease-in`, `scale(0)`. Enter starts from `scale(0.95)` with
  `opacity: 0`.
- UI animations are shorter than 300ms, exit is faster than enter, no bounce.
- Milliseconds and curves are written only in `tokens/motion.css`, keyframes only in
  `tokens/keyframes.css`. Components use them through `--motion-*`. No millisecond numbers in TS: use
  `motionMs("--dur-base")`.
- Motion tokens:
  - curves: `--ease-out` cubic-bezier(0.23, 1, 0.32, 1), `--ease-in-out`
    cubic-bezier(0.77, 0, 0.175, 1), `--ease-drawer` cubic-bezier(0.32, 0.72, 0, 1);
  - durations, ms: `--dur-instant` 80, `--dur-press` 140, `--dur-fast` 160, `--dur-fast-exit` 110,
    `--dur-base` 200, `--dur-exit` 140, `--dur-panel` 260, `--dur-slow` 320, `--dur-draw` 900;
  - other: `--stagger` 40ms, `--press-scale` 0.97, `--press-scale-surface` 0.99.
- Hover works only inside `@media (hover: hover) and (pointer: fine)`. Focus is not animated; one
  shared `:focus-visible` for everything. Keyboard-initiated actions are not animated.
- Pagination, scroll-to-element, cached data and colour changes are not animated.
- Frequency decides: values that change every tick are not animated (`tabular-nums`); only rare events
  get expressive motion.
- FLIP is interruptible: a new move starts from the visible position.
- A skeleton appears after 200ms and stays at least 300ms. A spinner appears after 400ms. When data is
  already present, use the `stale` dimming.
- Behaviour of common elements:
  - buttons: `:active` scale 0.97 (surfaces 0.99); a pending button does not shrink, keeps its width
    and sets `aria-busy`;
  - screen change goes through the router's `viewTransition` (`ButtonLink`, `Link viewTransition`);
    in-page layout changes go through `withViewTransition`;
  - first load: cards appear staggered with `calc(var(--i) * var(--stagger))`;
  - content swap goes through `Swap`;
  - `Disclosure` animates clip-path and opacity; a second click reverses from the current frame;
  - `Select`, `Menu`, `Popover`, `Combobox`: fade, scale 0.95→1 and a 4px shift from the anchor,
    `transform-origin` at the anchor, transitions via `@starting-style`, closing faster than opening;
  - `Dialog`: backdrop fades, panel scales, focus goes to the title, body has
    `overscroll-behavior: contain`;
  - `Checkbox` draws the tick via `stroke-dashoffset`, `Switch` moves the thumb via transform, `Radio`
    dot uses opacity and scale;
  - `Tooltip`: fade and scale 0.95; the next tooltip within the delay shows without animation;
  - toasts enter from the side and leave faster; errors stay 10s, others 5s; hover pauses; toasts
    live in `aria-live`.
- Reduced motion softens motion instead of removing it: `--dur-*` become 1ms, `--stagger` 0, shifts and
  scale are neutralised. Elements with `data-motion="fade"` get a short fade.
- Animate only through the `shared/motion/` primitives: `usePresence`, `useLatched`,
  `<Swap swapKey>`, `useSlidingIndicator`, `withViewTransition`, `motionMs`, `readEasing`,
  `useReducedMotion`, `useLoadingIndicator`.
- Motion tests assert: no literal ms, `cubic-bezier` or `!important` in CSS outside `tokens/`; every
  `--motion-*` points to an existing keyframe; every `*-exit` is shorter than its enter; reduced motion
  compresses every `--dur-*`.

## 6. Own controls

All controls are ours, one component per role:

- `Button` — a styled `<button>` inside features is forbidden;
- `Select` — native `<select>` is forbidden;
- `Combobox` and `TagInput` on top of `Popover` — home-made absolute layers are forbidden;
- `Menu` and `Popover` inside a shared `LayerHost`;
- `Checkbox`, `RadioGroup`, `Switch` — bare checkbox and radio are forbidden;
- `NumberField` — `type=number` with spinners is forbidden;
- `ScrollArea` plus global token-based scrollbars;
- `Disclosure` — bare `<details>` is forbidden;
- `Dialog` and `CloseButton`; an X icon anywhere else is forbidden;
- `Segmented`, `Tabs`, `Stepper`;
- `StatusBadge` (icon plus text) — status by colour alone is forbidden;
- `Stat` (`tabular-nums`), `Card` (`title`, `eyebrow`, `actions`);
- `EmptyState`, `ErrorState`, `Skeleton`, `Spinner`, `Banner`, `Toast`;
- `NoValue` instead of hand-written `—`, `-`, `n/a`;
- `Icon` — raw SVG and emoji inside features are forbidden.

Icons are mandatory on navigation items, action buttons, statuses, field prefixes and empty states
(48px). No icons above section titles or inside prose. An icon button has `aria-label` and a tooltip; a
decorative icon has `aria-hidden`. One concept, one icon, one canonical name.

Country flags come only from `flag-icons` through a `Flag` component; logos of companies, partners and
technologies only from theSVG, downloaded into `src/shared/ui/brand-logos/`. Never emoji flags, CDN
links or hand-drawn logos. How to fetch both: skill `asset-sources`.

Primitives are added when needed, but immediately by these rules: the second screen never writes its
own version of what the first one already has.

## 7. Styles

- Global styles live only in `shared/styles/`. `global.css` pulls `reset.css` and
  `tokens/{palette,semantic,radius,space,typography,elevation,motion,keyframes}.css` and is imported
  once in `main.tsx`.
- Everything else is a CSS Module next to its component. A module is imported only by its component,
  selectors start with the component class, no unused classes.
- A block of 3+ identical declarations in two places is forbidden: make a component or a token.
- Literal colours, durations, curves, shadows, radii and line widths live only in `tokens/`. Components
  use the semantic layer (`--surface-*`, `--text-*`, `--action-*`, `--border-*`, `--focus-ring`),
  never the palette directly.
- Two themes, light and dark. The semantic layer is defined twice, in `:root[data-theme="light"]` and
  `:root[data-theme="dark"]`. Components know nothing about the theme. The switch has exactly two
  options, light and dark; there is no "system" option. Until the user picks one, the theme follows
  the system setting (and its changes); the pick is kept in `localStorage` and wins from then on. The
  theme is applied before first paint with no flash. A test
  asserts every token exists in both themes.
- The site uses the full screen width; a narrow centred column is forbidden (AI pattern):
  - pages and work areas have no `max-width`;
  - gutters 24px, from 75rem — 32px;
  - width is filled with panels: sidebar, list with detail, filters with results;
  - grids use `minmax()` and `fr`;
  - width limits only for prose (≤ 70ch) and a single field (≤ 480px).
- Breakpoints only `30/48/64/75/90/120rem`; the same values in `matchMedia`.
- Radius, shadow, text size and spacing scales are fixed by tokens. No gradients and no emoji in the UI.
- Fonts are local (`@fontsource-variable/*` or `public/fonts`) with `font-display: swap`. No external
  assets or CDNs: the demo must work offline.

## 8. Accessibility

- Contrast at least 4.5:1 in both themes.
- Touch targets at least 44px.
- `:focus-visible` is always visible.
- State is never conveyed by colour alone.
- `Select`, `Menu` and `Combobox` work from the keyboard: arrows, Home/End, Esc and focus return.
- e2e runs with axe. Tests cannot see geometry, focus or alignment: a live browser pass is required
  before a feature ships.

## 9. Checks in `scripts/checks/`

- Every rule is pinned by a script: an agreement without a check comes back. A guard counts only if it
  was deliberately broken and the check failed under its own name.
- `npm run rules` runs all checks in a single process; `npm run rules -- --only <id>[,<id>]` runs a
  subset.
- A new rule is a new file in `scripts/checks/rules/<code|text|css|motion>/` exporting a `Check`, plus
  a line in `scripts/checks/registry.ts`. `tests/scripts/checks/engine.test.ts` fails when a rule file
  is not registered.
- When rules are introduced into existing code, record a ratchet baseline with
  `npm run rules -- --record-missing` (`scripts/baselines/<id>.txt`). Recorded violations may only
  shrink; `--prune` lowers the baseline after fixes.
- Checks: file-length, no-comments, package-size, package-subject, import-cycles, layers,
  raw-requests, no-mocks, page-titles, motion-libraries, ui-kits, remote-assets, icon-alias,
  consistency, cyrillic, jsx-text, text-separators, symbol-glyphs, no-emoji, css-literals, css-token-refs, css-modules,
  global-styles, css-duplicates, css-transitions, scale-tokens, token-layers, theme-parity, contrast,
  no-side-stripe, no-gradients, page-width, touch-targets, hover-gate, motion-tokens, ts-timings.
- `npm run api:types` regenerates `schema.gen.ts` from `API_SCHEMA_URL` (needs network once for
  `openapi-typescript`). The home page polls `GET /api/v1/health` and shows an honest error with retry
  until the backend exists.

## 10. The cycle for every screen

The bar: a product you could put next to Linear, Stripe and Raycast.

1. **Shape before code.** `impeccable shape <screen>`: task, states, hierarchy, panels;
   `ui-ux-pro-max` checks against domain rules. Output: a screen spec in `work/screens/<screen>.md`.
2. **Build.** `impeccable` new work from the spec, only from `shared/ui`.
3. **Motion.** `find-animation-opportunities` on the screen, `animate` for each chosen spot, then
   `review-animations`. **Edges:** `break-ui` with worst-case data.
4. **Live check** on seeded demo data from the running backend: `npm run shots` captures the matrix — widths 375, 768, 1024, 1440, 1920
   × light and dark × ru and en × loading, error, empty. Look at the shots with your own eyes: tests do
   not see the screen.
5. **Critique.** `impeccable critique`; every P0 and P1 is fixed before the next screen. Then
   `impeccable audit`.
6. **Polish.** `impeccable polish`, texts via `clarify`, edges and errors via `harden`, empty states
   via `onboard`.

### A screen is not done if

- there is a narrow centred column with empty margins;
- identical cards in a grid "icon, title, text";
- all-caps labels above every section, numbering 01, 02, 03 without a real sequence;
- the "big number, caption, gradient" template;
- gradient text, glass for the sake of glass, a coloured stripe on the side of a card;
- "—" or "·" used as a separator, emoji instead of an icon;
- text below 4.5:1 contrast in either theme;
- the same enter animation on every section; motion that communicates nothing;
- an element behaves differently from the same element on a neighbouring screen;
- a paragraph of explanation where a signature data component would do;
- generic phrases instead of specific ones;
- `null` or a "Loading…" text instead of a skeleton; an error without "Retry";
- anything breaks at 375px width or in either theme.
