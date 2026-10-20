# Audit file format

Copy into `work/audits/frontend-<n>.md` and fill every section. Write it in the language of the
repo docs; this file only fixes the structure.

```markdown
# Frontend audit <n>: <audits covered>

Scope: audits <1-5>, routes <list>, commit <sha>, <date>.

## How we checked

- Matrix: widths <375, 768, 1024, 1440, 1920>, themes <light, dark>, languages <ru, en>,
  states <live, loading, error, empty>.
- Commands and results: `npm run verify` <result line>, `npm run e2e` <result line>,
  `npm run shots -- ...` <count of screenshots>.
- Measurements: <CLS per route, animation durations, focus checks> with the method used.
- Screenshots: `work/audits/frontend-<n>/before/`, `work/audits/frontend-<n>/after/`.

## Summary

<Three to five lines: what is strong, what blocks the demo.>

| Dimension | Score 0-4 | Main issue |
|---|---|---|
| Motion | | |
| UX and scenarios | | |
| Visual system | | |
| Air, rhythm, scaling | | |
| Anti-AI-slop and polish | | |

Findings: P0 <n>, P1 <n>, P2 <n>.

## Findings

### P0: breaks the scenario or accessibility

#### 1. <Short title>

- **Where:** <route, state, width, theme>; `<file>:<line>`.
- **What is wrong:** <observable behaviour>, screenshot `<path>`.
- **Fix:** <token or shared component to change>.
- **Check:** <test, e2e step or screenshot that proves it>.
- **Status:** open | fixed in <sha> | won't fix: <reason>.

### P1: clearly visible

### P2: polish

## Before and after

| Finding | Before | After |
|---|---|---|
| 1 | `before/<route>/<file>.png` | `after/<route>/<file>.png` |

## Not checked

<What was out of reach and why: real devices, screen readers, slow network.>
```

Scores: 0 broken, 1 poor, 2 works with major issues, 3 good with minor issues, 4 nothing to fix.
