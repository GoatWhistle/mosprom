---
name: modern-web-guidance
description: "Use when implementing or reviewing web platform features; select the relevant guide and check current API docs."
---

# Modern Web Guidance

An offline library of best-practice guides for modern web platform features: one guide per use case, stored as `guides/<category>/<id>.md`.

> **In this repo:** code examples in the guides are illustrative. Our code has no comments, so strip them when copying. In React, view transitions go through react-router 7 `viewTransition` or `document.startViewTransition` + `flushSync` (in `frontend/` the second path is `withViewTransition` from `shared/motion/`).

## When to use

Must use this skill:
- At the **start** of implementing any web feature.
- Before creating a new component, to check if a standardized pattern already exists.
- To avoid implementing ad-hoc solutions or loading large dependencies unnecessarily.

## Usage Instructions

### Step 1. Search the local guides

Search the local `guides/` folder with Grep/Glob and Read the matching guide. The file name is the guide id.

- Categories: `accessibility`, `css`, `forms`, `html`, `js`, `performance`, `ui-atoms`, `ui-behaviors`, `ui-components`, `visual-design`.
- Glob by use case in the file name, e.g. `guides/**/*transition*.md`, `guides/**/*dialog*.md`, `guides/**/*scroll*.md`.
- Grep the guide contents for the feature or API, e.g. `startViewTransition`, `animation-timeline`, `@starting-style`, `anchor-name`, `fetchpriority`, `content-visibility`.
- If nothing specific matches, start from the broad overview guides: [`accessibility`](guides/accessibility/accessibility.md), [`css`](guides/css/css.md), [`css-layout`](guides/css/css-layout.md), [`forms`](guides/forms/forms.md), [`html`](guides/html/html.md), [`web-components`](guides/html/web-components.md), [`performance`](guides/performance/performance.md), [`motion`](guides/ui-behaviors/motion.md), [`color`](guides/visual-design/color.md), [`typography`](guides/visual-design/typography.md), [`visual-effects`](guides/visual-design/visual-effects.md).

---

### Step 2. Read the best practices

Read the whole matching guide; read several when the task spans several use cases. Guides link to related guides by relative path; follow a link when the task touches it. A reference marked "not in the local `guides/` folder" names an upstream guide that was not vendored.

---

### Step 3. Verify Guidance Compliance

When generating or modifying code, cross-check the implementation against the retrieved guide before concluding:
- **Applicable Guidance & Fallbacks**: Ensure the relevant modern patterns and necessary fallback strategies from the guide are correctly applied, without forcing unrequested features.
- **Task Fulfillment**: Confirm that the implementation fully satisfies the user's request.

## Guidelines

- Always search the local guides **first** to find the most relevant ones.
- These guides are usually framework-agnostic; adapt them correctly to your setup.
- Do not hallucinate guides or ignore them; they represent the preferred local standard for the user's project.

## Interpreting Browser Support & Fallbacks

* **Default Behavior**: All guides assume **Baseline Widely available** features are safe to use without fallbacks. For features that are not Baseline widely available, you **MUST** follow the fallback recommendations in the guide, unless the user has specified a custom browser support policy.
* **Custom Policies**: If the user has already defined explicit browser support requirements, use the browser compatibility data in the guide to determine if a fallback can be safely ignored.
  - For Baseline YYYY targets, a feature satisfies this target if its "Baseline since" date is <= YYYY.
  - **Policy Examples**:
    - _"Do not implement feature fallbacks."_ (for exploratory prototypes of the cutting-edge web)
    - _"Safari 17.4+"_ (for internal tools targeting macOS or Tauri-based desktop apps)
    - _"Never recommend or implement polyfills; if a Baseline Newly Available feature is required for core functionality, provide a lightweight custom fallback or redesign the approach."_ (to minimize bundle size and avoid technical debt)
    - _"Assume a modern execution environment where Baseline Newly Available features can be used natively, provided they are strictly feature-detected and degrade gracefully."_ (for progressive enhancement strategies)
* **Reactive Policy Discovery**: Watch for environmental cues to suggest documenting a policy in CLAUDE.md or AGENTS.md. Suggest this if the developer:
  - Mentions building for a restricted runtime (e.g., Electron or Tauri).
  - Explicitly excludes specific targets (e.g., "we don't support Desktop Chrome").
  - Expresses hesitation about polyfill complexity, bundle size, or performance cost.
  - Questions if a feature is safe to use without fallbacks.

  No defined policy format. This is an example: `**Browser Support:** Allow Newly Available features, but only adopt custom fallback code that adds <= 20 lines and does not require external dependencies.`
