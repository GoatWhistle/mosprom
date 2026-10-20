# What each audit checks

The matrix for every audit: widths 375, 768, 1024, 1440, 1920 (plus 2560 for audit 4), light and
dark, ru and en, states live, loading, error and empty. Screens are looked at, not only tested.

## 1. Motion

- Enter and exit of every overlay, menu, popover, dialog, toast, disclosure; exit faster than entry.
- Content changes go through `Swap`, first load staggers cards, screen changes use View
  Transitions, skeleton to content has no jump.
- Only `transform`, `opacity`, `clip-path` and blur up to 2px move; nothing starts at `scale(0)`;
  no `ease-in`, no bounce; UI animations under 300ms; hover only behind the pointer media query;
  focus never animates; keyboard actions are instant.
- Reduced motion: emulate it and repeat the pass; feedback must still be visible as a fade.
- No double animation (parent and child both moving), no animation on cached data or colour change.

Measure:

```js
document.getAnimations().map((a) => ({
  target: a.effect?.target?.className,
  duration: a.effect?.getTiming().duration,
  easing: a.effect?.getTiming().easing,
}))
```

```js
let shift = 0
new PerformanceObserver((list) => {
  for (const entry of list.getEntries()) if (!entry.hadRecentInput) shift += entry.value
}).observe({ type: "layout-shift", buffered: true })
```

CLS above 0.1 on any route or state is a P1; above 0.25 is a P0.

## 2. UX and scenarios

- The P0 scenario end to end: count clicks, note every place a user hesitates, every dead end.
- Every state of every list and panel: loading (skeleton, not text), empty (why and what next),
  error (key from `errors:*` plus retry), stale, offline.
- Keyboard: Tab order, Esc closes and returns focus, arrows in menus and selects, visible ring;
  check `document.activeElement` after closing each dialog and after route changes.
- URLs: the current view (filters, selection, tab) survives reload and can be shared.
- Copy in ru and en: short, concrete, the same word for the same thing on every screen; no
  backend `message` shown to the user.

## 3. Visual system

- Colour roles from `DESIGN.md` hold everywhere: accent only for its meaning, status never by
  colour alone, no palette token used in a component (`npm run rules` reports it).
- Type: only scale tokens, one title style per level, tabular numbers where values align.
- Same element, same look and behaviour on every screen: buttons, cards, empty states, icons
  (one concept, one icon).
- One-off styles: a declaration that exists on one screen only is a candidate for a token or a
  component.
- Update `DESIGN.md` when a role or rule changed.

## 4. Air, rhythm, scaling

- Spacing comes from the scale; vertical rhythm is consistent inside cards and between sections.
- 1920 and 2560: panels fill the width, no empty side fields, no stretched lines of text.
- 375: no horizontal scroll, long words and numbers wrap or truncate with a tooltip, header and
  actions stay reachable, touch targets 44px.
- 200% zoom: open the page at 720px viewport width with `deviceScaleFactor: 2` and check reflow.
- Large system font: add `html { font-size: 125% }` through `page.addStyleTag` and repeat 375 and
  1440.

## 5. Anti-AI-slop and polish

- Walk the "screen is not ready if" list in `frontend/AGENTS.md`, section 10, and the
  anti-references in `PRODUCT.md`, one line at a time.
- Look for: gradients for decoration, glass, glows, identical icon cards, KPI tiles without a
  conclusion, centred hero blocks inside the app, caps-lock eyebrows, fake numbering, separators
  made of dashes or dots, emoji, marketing phrases, paragraphs where a data component would do.
- Microdetails: alignment to the grid, optical balance of icons and text, consistent corner radii,
  numbers formatted by locale, empty states with a real next step.
- Finish with `impeccable critique` and `impeccable polish` on the worst two screens.
