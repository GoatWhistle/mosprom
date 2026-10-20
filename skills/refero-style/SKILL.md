---
name: refero-style
description: "Use when extracting a visual system from a Refero style selected by the user."
---

# Refero style

Refero Styles (<https://styles.refero.design/>) is a library of 2,000+ design systems extracted from
real product sites. Each style has a page `https://styles.refero.design/style/<uuid>` with the source
site, tokens, type, spacing, radii, shadows, components, do and don't, an agent prompt guide and
exports. The user chooses the style; the agent never picks one, never proposes "the best" one and
never starts from a style it likes. Hard rules in `frontend/AGENTS.md` still apply on top.

## 1. Ask the user to pick

Send one message:

- the link <https://styles.refero.design/> and how to browse: Trending, Popular, Newest tabs, mood
  tags (for example "Swiss grid editorial", "Zero border radius"), search;
- what matters for this product, taken from `frontend/PRODUCT.md` and the thesis (users, register,
  mood words), so the user knows what to look for;
- the request: send the link of the chosen style page, and say whether a light or dark first screen
  is wanted.

Then stop and wait. Done when the user has sent a `styles.refero.design/style/<uuid>` link.

## 2. Pull the style

Use the Refero MCP if it is connected (setup: <https://refero.design/mcp>, works with Claude,
ChatGPT, Cursor, Codex); otherwise fetch the style page. Collect all of it, nothing summarized away:

| Field | What to record |
| --- | --- |
| Identity | Style name, tagline, theme (light or dark), one-paragraph description, the style page URL |
| Source site | The exact URL of the site the style was extracted from |
| Colors | Every token: name, hex, CSS variable; accents, neutrals, surfaces (canvas, card, inverted) |
| Typography | Families with fallbacks, weights, sizes, line heights, letter spacing, the full type scale |
| Spacing and layout | Density, max width, section gap, card padding, element gap, spacing scale |
| Shape and depth | Radii per element (nav, card, button, pill), shadows and elevation values |
| Components | The named component list and the agent prompt guide examples |
| Guidelines | Every Do and Don't verbatim |
| Exports | The DESIGN.md text (tab "DESIGN.md" or the "Copy.md" button), the CSS Variables, Tailwind v4 and Design Tokens tabs |
| Similar brands | The related styles listed on the page |

Save it to `work/design/style.md` (internal, removed before the defense), DESIGN.md text included
verbatim. Done when every row above is filled or marked "not on the page".

## 3. Study the source site

Open the source site from step 2 with Playwright or the browser tools: home page and one inner page,
desktop 1440 and mobile 375, light and dark if it has both. Note how the tokens are actually used:
hierarchy, density, how buttons, cards, tables and empty states look, how motion feels. Save 4–6
screenshots to `work/design/source/` and three observations per screenshot in `style.md`.

## 4. Map onto the product

1. **Conflicts first.** List every point where the style contradicts `frontend/AGENTS.md` (gradients,
   glyph prefixes like ▲ or ✓, narrow centered column, glass, motion beyond our tokens, UI kits) and
   ask the user in one message which way each goes. Our accessibility rules (contrast 4.5:1, 44 px
   targets, focus) are never traded away.
2. **Colors.** Style neutrals and accents into `src/shared/styles/tokens/palette.css`; the semantic
   layer (`--surface-*`, `--text-*`, `--action-*`, `--border-*`, `--status-*`) for both themes. A
   style with only one theme gets the second derived from its own neutrals, checked for contrast.
3. **Type.** The style families as local fonts (`@fontsource-variable/*` when available, otherwise
   files in `public/fonts` with their licence). A font that is not open or not obtainable gets the
   style's own fallback, said to the user.
4. **Space, shape, depth.** Spacing scale, radii and elevation tokens from the style; motion tokens
   stay ours.
5. **Words.** `frontend/DESIGN.md`: color roles, type, shape, layout, components, Do and Don't from the
   style adapted to the product. `frontend/PRODUCT.md`: Brand Personality and Anti-references.
6. **Propagate.** `cd frontend && npm run tokens:export -- --fonts`, `npm run verify`,
   `npm run shots`; `cd presentation && npm run build && npm run readme`.

Done when the frontend checks pass in both themes, the shots look like the source site's language
applied to our product, and the deck and README render in the new style.
