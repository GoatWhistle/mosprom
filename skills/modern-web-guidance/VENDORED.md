# Vendored: modern-web-guidance

- Upstream: https://github.com/GoogleChrome/modern-web-guidance, path `skills/modern-web-guidance`
- License: Apache-2.0, see [LICENSE](LICENSE) (kept unchanged)
- Upstream commit date: 2026-10-07; `guides/` taken at commit `a972868`; upstream `SKILL.md` was pinned to skill version `2026_09_04-7de96777`
- Vendored: 2026-10-10

## Local edits

1. `SKILL.md` made fully offline. Retrieval through `npx -y modern-web-guidance@latest search|list|retrieve` was replaced with searching the local `guides/` folder with Grep/Glob and reading the matching guide. The npx/pnpx usage section and the example JSON output were removed, and a list of the broad overview guides was added as relative links.
2. `SKILL.md` description: the "MANDATORY: Execute FIRST" wording became a normal trigger-rich description.
3. `SKILL.md`: added a note at the top. Code examples are illustrative; our code has no comments, so strip them when copying. React view transitions go through react-router 7 `viewTransition` or `document.startViewTransition` + `flushSync`.
4. `guides/**`: 74 in-guide references of the form `` `id` (via `npx -y modern-web-guidance@latest retrieve "id"`) `` in 26 files were rewritten. 72 became relative markdown links to the local guide file; every target was checked to exist.
5. `guides/forms/sms-otp-form.md` (`passkeys`) and `guides/visual-design/equal-width-text-lines.md` (`fit-text-to-container`) name upstream guides that are not in the local folder. Those two references became plain text naming the guide.
