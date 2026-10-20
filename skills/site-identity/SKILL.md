---
name: site-identity
description: "Use when adding browser and app icons, manifest, social cards or localized page titles."
---

# Site identity: icons, cards, tab titles

The tab, the home screen icon and the link preview are the product's first impression. They come
from one source each and are regenerated, never drawn by hand.

| Source | Where |
| --- | --- |
| The mark | `docs/brand/symbol.svg` (skill `brand-identity`), otherwise `<template id="brand-mark">` in `presentation/src/shell.html`; parts carry `class="mark-base"` and `class="mark-accent"` |
| Colors | the site tokens in `frontend/src/shared/styles/tokens/` (`--text-primary`, `--action-primary`, `--surface-base`, `--surface-raised`, `--text-secondary`, `--border-subtle`) |
| Name, tagline, description | `common:app.name`, `common:app.tagline`, `common:meta.description` in `frontend/src/shared/i18n/locales/{ru,en}/common.json` |
| Public address | `SITE_URL` in `.env` (passed to the Docker build), used for absolute card links |

## 1. Generate

```bash
cd frontend && npm run brand:assets
```

writes into `frontend/public/`:

| File | Who uses it | How it looks |
| --- | --- | --- |
| `favicon.svg` | Every modern browser tab | The mark, recolored for the light and dark tab by `prefers-color-scheme` inside the file |
| `favicon.ico` (16, 32, 48) | Old browsers, Windows shortcuts, crawlers that ask for `/favicon.ico` | The mark on a rounded raised tile, readable on light and dark tab bars |
| `apple-touch-icon.png` (180) | iOS and iPadOS home screen, Safari bookmarks | Opaque base surface, the mark at 62%; iOS rounds the corners itself |
| `icons/icon-192.png`, `icons/icon-512.png` | Android home screen, PWA install, splash screen | Opaque base surface, the mark at 62% |
| `icons/icon-maskable-512.png` | Android adaptive icons (circle, squircle, teardrop) | Full bleed, the mark at 50% inside the 80% safe zone |
| `site.webmanifest` | Install prompt, Android task switcher | Name, description, language, colors from the tokens, the icons above |
| `og/og-ru.png`, `og/og-en.png` (1200 x 630) | Telegram, VK, LinkedIn, X, Slack, WhatsApp, Discord link previews | Light site surface, mark and name, the tagline large, the description, the address |

`index.html` already links all of it, plus `theme-color` for both themes (the browser chrome on
mobile follows the theme), `apple-mobile-web-app-title`, Open Graph and Twitter tags. The card in the
tags is the RU one (`META_LOCALE` in `scripts/brand/assets.ts`); switch it to `en` for an
international hackathon.

Not generated on purpose: `browserconfig.xml` and Windows tiles (dead since Edge on Chromium),
Safari `mask-icon` (Safari uses the SVG favicon since version 14), dozens of legacy Apple sizes (one
180 px icon is scaled by iOS).

## 2. Tab titles

Format, enforced in code (`src/shared/i18n/document-title.ts`), the only place `|` is allowed:

| Page | Title |
| --- | --- |
| Home (`/`) | `Product | tagline`, from `app.name` and `app.tagline` |
| Any other page | `Page | Product` |
| Not found, errors | `Страница не найдена | Product` |

- Every page component in `src/pages/*/` calls `useDocumentTitle(t("<ns>:title"))`; the home page
  calls `useDocumentTitle(null)`. The `page-titles` check fails a page without it.
- The page part is the page's own heading word for word, from the dictionary, in the current
  language; the title switches with the language.
- Short: the page part two or three words, the product name at most 24 characters, the home title at
  most 60 (a test checks both languages). No emoji, no em dashes, no product slogans in inner pages.
- The static `<title>` and `og:title` in the built HTML are the home title, so the tab is right before
  JavaScript runs and link previews read the same text.

## 3. Check

`npm run verify` covers it: `tests/scripts/brandAssets.test.ts` fails when `favicon.svg` no longer
matches the mark and tokens (run `npm run brand:assets`), when an icon has the wrong size, the ICO
lacks a size, the manifest points to a missing file or `index.html` lacks a tag; the title tests and
`page-titles` cover the tabs.

Then look with your own eyes:

1. The tab in Chrome and Firefox, light and dark system theme: the mark is crisp at 16 px and
   visible on both tab colors.
2. `og/og-ru.png` and `og/og-en.png` at full size and at 400 px wide: the tagline reads, nothing is
   cut.
3. On the deployed stand with `SITE_URL` set: paste the link into Telegram and one other network
   and check the preview; a cached old preview is refreshed by the network's own tool
   (`@WebpageBot` in Telegram, LinkedIn Post Inspector).

Done when `npm run verify` is green, the four looks above were done, and the product name, tagline and
mark in the tab, on the home screen and in the link preview are the same as in the README and the
deck.
