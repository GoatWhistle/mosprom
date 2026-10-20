---
name: brand-identity
description: "Use when choosing or exporting a product logo and brand kit, with size and background checks."
---

A mark is judged at 16px in a browser tab and at 3 metres on a projector. Design for those two first; everything else follows.

Prerequisite: a chosen name and tagline (`naming`, see `work/naming.md`). The default path uses hand-written SVG. Optional vendor workflows `logo-design` and `design` require explicit user invocation; they are not prerequisites.

## 1. Variants gallery

Build `work/brand/logo-gallery.html` — one self-contained page, no external assets:

- variants are numbered and the numbers persist across series (1–5, then 6–10 develops the favourites, 11–20 refines); never renumber;
- cover every architecture at least once: wordmark, lockup (symbol + word), symbol only, letterform-as-symbol, monogram;
- at least one variant uses the typographic device from `work/naming.md`;
- each variant is shown on light, dark and accent backgrounds, at 16, 32, 64 and 256px, in one colour and inverted;
- a "lives in the product" strip: browser tab with favicon, app header, deck cover, README header;
- a favourites toggle per variant kept in `localStorage`.

Draw on a grid with geometric primitives; strokes and corner radii come from a small set of values. No gradients, no glows, no stock icons, no letters from a font converted without adjustment.

Done: the user has picked one variant by number.

## 2. Export the kit

Record the choice and rationale in `work/brand/brand.md`, then produce:

- `docs/brand/wordmark-light.svg`, `docs/brand/wordmark-dark.svg`, `docs/brand/symbol.svg` — optimized, `viewBox` set, no embedded raster, text converted to paths;
- the symbol paths split into `mark-base` and `mark-accent` parts, the same split as the deck's `brand-mark` template;
- then the skill `site-identity`: `cd frontend && npm run brand:assets` renders every favicon, the app and PWA icons, the manifest and the RU and EN social cards from `symbol.svg` and the tokens; its tests guard them.

## 3. Colour and voice

- Colours, type and shape come from the style the user picked (skill `refero-style`); the mark uses that palette. Without a picked style: one accent colour that carries meaning, neutrals tinted towards it, danger and success colours only for their meaning. Check 4.5:1 contrast for text in both themes.
- Values go only into `frontend/src/shared/styles/tokens/palette.css` and the semantic layer; then `npm run tokens:export` so the deck matches.
- Voice: three adjectives the product is, three it never is, and two example sentences in each language. Write them into `frontend/PRODUCT.md` (Brand Personality, Anti-references) and colour/type roles into `frontend/DESIGN.md`.

Done: the mark is visible in the app header, tab, README header and deck cover; all three read as one product.
