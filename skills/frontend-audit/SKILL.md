---
name: frontend-audit
description: "Use when auditing UI motion, scenarios, visual consistency and scaling; record findings in work/audits/."
---

# Frontend audit

Five audits in a fixed order, each answered with evidence from the running app, not from reading
code. From the repository root, read `frontend/AGENTS.md` for the area rules and
`frontend/PRODUCT.md` and `frontend/DESIGN.md` for the product and visual context.

| # | Audit | Question it answers |
|---|---|---|
| 1 | Motion | Does every change of state move once, briefly, from the right origin, and stay still where it should? |
| 2 | UX and scenarios | Can a user finish the P0 scenario without help, dead ends or lost focus? |
| 3 | Visual system | Is every screen built from the same tokens and components, with colour meaning one thing? |
| 4 | Air, rhythm, scaling | Does the layout hold at 375, at 1920+, at 200% zoom and with large system font? |
| 5 | Anti-AI-slop and polish | Is there anything a jury would recognise as a generated template? |

What to look at and how to measure each audit: [AUDITS.md](AUDITS.md). Audit file format:
[FORMAT.md](FORMAT.md).

## Steps

1. **Scope.** List the routes and the states each one can show (data, loading, empty, error).
   Take the next free number `<n>` in `work/audits/`. Default scope is all five audits over all
   routes; a narrower scope is written in the report header.
   Done when: routes, states and audits are listed in a new `work/audits/frontend-<n>.md`.

2. **Baseline.** Run `npm run verify` and `npm run e2e` (axe with `wcag22aa`) and record the result
   lines. Take the "before" matrix:
   `npm run shots -- --routes root,<route> --states live,loading,error --out ../work/audits/frontend-<n>/before`.
   Routes are written without the leading slash (`root` is `/`), so Git Bash does not rewrite them.
   Done when: verify and e2e results and the before screenshots are in place, red results included.

3. **Audit.** Go through the audits in order with the checklists in [AUDITS.md](AUDITS.md). Look at
   every screenshot; measure in the browser what screenshots cannot show (focus, animations,
   layout shift). Write each finding immediately: where, what is wrong, fix, how to check. Every
   number in the report carries the command or measurement that produced it.
   Done when: every audit has a score 0-4 and every checklist line is either passed or a finding.

4. **Prioritise.** P0 breaks the P0 scenario or accessibility, P1 is clearly visible to the jury,
   P2 is polish. Add the summary table and counts.
   Done when: the report matches [FORMAT.md](FORMAT.md) section by section.

5. **Fix.** Fix P0 and P1, then P2 as time allows. A fix changes a token in
   `src/shared/styles/tokens/` or a component in `src/shared/ui` or `entities`, never one screen's
   CSS around the problem. A rule that was broken gets a check in `scripts/checks/rules/` so it
   cannot come back. Motion fixes go through `review-animations` before they count.
   Done when: `npm run verify` and `npm run e2e` are green.

6. **Close.** Take the "after" matrix into `work/audits/frontend-<n>/after`, mark each finding
   `fixed` with the commit or `open` with the reason, update `DESIGN.md` when the visual system
   changed.
   Done when: no P0 or P1 is open without a written reason, and before/after pairs exist for every
   fixed visible finding.
