# Skills catalog

All skills live in this root `skills/` directory. Claude Code discovers them through
`.claude/skills/<name>` and Codex through `.agents/skills/<name>`; both are relative symlinks to
`skills/<name>`. The links are checked in, so a fresh clone has the same skills for both agents.

Edit skills here and read their references from this canonical path. After adding, removing or
renaming a skill, run `bash .claude/scripts/sync-agents.sh` (also called by `setup.sh`) and commit
the link changes with the source. Edits to an existing skill are shared immediately. The groups
below describe their purpose; every group is discoverable from the repository root. Read
`frontend/AGENTS.md` before UI work and `presentation/AGENTS.md` before defense work. Commands and
product paths in frontend skills use `frontend/` as cwd; presentation skills use `presentation/`
as cwd unless a step names another directory. References to files outside a skill use paths
from the repository root; supporting links within a skill are relative to its canonical directory.

"Manual" uses `disable-model-invocation: true` for Claude and
`agents/openai.yaml` with `policy.allow_implicit_invocation: false` for Codex. Invoke explicitly with
`/name` or `$name`; descriptions are not offered for automatic selection. Shared references may be
read by direct file pointer without invoking a manual workflow. Overlapping vendor toolkits stay manual;
the project workflows (`brand-identity`, `presentation`, `site-identity`) remain discoverable.

## Process, engineering, documentation and brand

| Skill | Mode | Use for | Origin |
| --- | --- | --- | --- |
| `hack-kickoff` | auto | first hours: `brief/` and `context/`, criteria, thesis, P0, timeline | own |
| `compact-context` | auto | keep `context/` under its budget: promote entries to their home, delete what is done | own |
| `naming` | auto | product name, tagline, name origin | own |
| `refero-style` | auto | the user picks a style on styles.refero.design; pull tokens, type, components, DESIGN.md, study the source site, map onto product tokens | own |
| `asset-sources` | auto | icons, flags from flag-icons, company logos from theSVG; no glyph icons, em dashes or dot separators | own |
| `brand-identity` | auto | logo gallery, mark export, colour and voice | own |
| `site-identity` | auto | favicons for every device and theme, PWA icons and manifest, RU and EN social cards, `Page | Product` tab titles, `npm run brand:assets` | own |
| `competitors` | auto | rivals, threat tiers, honest "where they beat us" | own |
| `readme` | auto | README in two phases, visuals rendered in the product's design system, hero shot | own |
| `repo-meta` | auto | GitHub description (rule plus definition, no AI patterns), homepage and 10–20 topics from the real stack, `meta.mjs scan/check` | own |
| `docs-writing` | auto | docs standard, evidence statuses, pre-submission docs audit | own |
| `jury-route` | auto | `docs/for-jury.md`, requirements map, criteria coverage | own |
| `submission` | manual | final day: platform checklist, fresh-clone run, scrub | own |
| `orchestrate-issues` | manual | autonomous run of an issue queue in worktrees | own |
| `to-spec` | manual | conversation → spec issue | mattpocock |
| `to-tickets` | manual | spec → tracer-bullet tickets with blockers | mattpocock |
| `triage` | manual | triage labels state machine, agent briefs | mattpocock |
| `implement` | manual | implement a ticket or spec | mattpocock |
| `wayfinder` | manual | big fuzzy work as a map of decision issues | mattpocock |
| `grilling` | auto | relentless interview on a plan | mattpocock |
| `grill-with-docs` | manual | grilling plus domain docs | mattpocock |
| `domain-modeling` | auto | glossary and ADRs | mattpocock |
| `codebase-design` | auto | deep modules vocabulary | mattpocock |
| `improve-codebase-architecture` | manual | find deepening opportunities, HTML report | mattpocock |
| `diagnosing-bugs` | auto | hard bugs and regressions | mattpocock |
| `tdd` | auto | red → green → refactor | mattpocock |
| `prototype` | auto | throwaway prototype for a design question | mattpocock |
| `research` | auto | primary-source research into a markdown file | mattpocock |
| `handoff` | manual | persistent context/SESSION.md handoff | mattpocock |
| `pr` | auto | PR body: summary, evidence, merge danger | mattpocock |
| `writing-for-agents` | auto | writing skills and `AGENTS.md` | mattpocock |
| `design-system` | manual | token architecture, slide generation helpers | ui-ux-pro-max |
| `design` | manual | logo/icon/CIP generation (needs `GEMINI_API_KEY` or another provider) | ui-ux-pro-max |
| `brand` | manual | brand voice and consistency | ui-ux-pro-max |
| `slides` | manual | HTML slide strategies and copy formulas | ui-ux-pro-max |
| `logo-design` | manual | depth reference for marks; process is `brand-identity` | rampstackco |
| `humanizer` | auto | remove AI-writing tells from prose | blader |
| `modern-web-guidance` | auto | native platform patterns, offline guides | GoogleChrome |

## Frontend

| Skill | Mode | Use for | Origin |
| --- | --- | --- | --- |
| `impeccable` | auto | design, critique, audit, polish, harden, clarify, onboard | pbakaus |
| `ui-ux-pro-max` | auto | UX rules, a11y checks, searchable design data | ui-ux-pro-max |
| `frontend-design` | auto | aesthetic direction for new surfaces | Anthropic |
| `frontend-audit` | auto | the five audits before polish | own |
| `animate` | auto | build a new animation step by step | emilkowalski |
| `emil-design-eng` | auto | polish and motion philosophy | emilkowalski |
| `review-animations` | manual | strict motion review against `STANDARDS.md` | emilkowalski |
| `improve-animations` | auto | motion audit and plans | emilkowalski |
| `find-animation-opportunities` | auto | where motion is missing | emilkowalski |
| `animation-vocabulary` | auto | the name of an effect | emilkowalski |
| `break-ui` | auto | worst-case data stress test | emilkowalski |
| `fixing-motion-performance` | auto | compositor-only motion, layout thrash | ibelick |

## Presentation

| Skill | Mode | Use for | Origin |
| --- | --- | --- | --- |
| `presentation` | auto | any deck or speech request: structure, text, vibe or edit; deck and speech in sync | own |
| `pitch-deck` | auto | deck from criteria and evidence, slide cards, variants | own |
| `speaker-script` | auto | 6-minute `SPEECH.md` per slide, timing, handoffs, `speech:check`/`speech:sync` | own |
| `pitch-craft` | auto | the spoken words: beats, word budget, hook, close | ooiyeefei |
| `demo-runbook` | auto | demo scenario, plan B, backup recording | own |
| `jury-qa` | auto | Q&A prep, uncomfortable questions, red lines | own |
| `deck-audit` | auto | can the jury answer from the deck alone | own |
| `deck-motion` | auto | slide choreography, steps, runners, counters | own |
| `deck-cover-final` | auto | animated logo cover, final slide with «Готовы к вашим вопросам» and QR assembly | own |
| `deck-design-sync` | auto | deck matches the product 1:1: tokens, fonts, radii, icons, data components | own |
| `storytelling-with-data` | auto | charts and data slides | sammcj |
| `video-script` | auto | 5-minute video script from the live site, RU or EN, voice-over and captions, `video:check`/`video:shots` | own |
| `linkedin-post` | auto | LinkedIn post per team member: images in product tokens, carousel PDF, feed preview, text checks | own |
| `video-thumbnail` | auto | YouTube thumbnail in the product tokens, four layouts, feed preview, title proposals | own |
| `pitch-video` | auto | recording, assembly and render via `hyperframes`, upload checks | own |
| `submission-texts` | auto | character-limited forms, social posts and cards | own |
| `banner-design` | manual | banners and social images | ui-ux-pro-max |

## Plugins kept as plugins

`.claude/settings.json` enables `hyperframes` (video and motion compositions), `context7` (current
library docs) and `superdesign` (design canvas). The plugin versions of `impeccable`, `ui-ux-pro-max`
and `frontend-design` are disabled at project level because the vendored copies above replace them.
`impeccable`'s live detector hooks are machine-local: `/impeccable hooks on` once per machine.

## Precedence

A personal skill in `~/.claude/skills/` with the same name overrides the project one. If a personal
`logo-design` or `impeccable` exists, update or remove it so the project version is used.

## Origins and updates

| Source | Licence | Version used | Local edits |
| --- | --- | --- | --- |
| [mattpocock/skills](https://github.com/mattpocock/skills) | MIT | `49dd158` (2026-10-09) | `triage`: mandatory AI disclaimer removed. `resolving-merge-conflicts` dropped (removed upstream). `/setup-matt-pocock-skills` is replaced by the tracker section of `AGENTS.md` and `.claude/tracker.md`; their `GLOSSARY.md` is `docs/glossary.md`. |
| [emilkowalski/skills](https://github.com/emilkowalski/skills) | MIT | `e8a175d` (2026-10-02) | none; `LICENSE` copied into each folder |
| [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | Apache-2.0 | 4.5.2, `d631a88` (2026-10-08) | plugin build of the skill (portable paths) |
| [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | MIT | `50d8a7d` (2026-10-09) | `${CLAUDE_PLUGIN_ROOT}` paths → `${CLAUDE_SKILL_DIR}`; `ui-styling` dropped (prescribes Tailwind and shadcn); `design-system`, `design`, `brand`, `slides` kept together at root because they reference each other |
| [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) `frontend-design` | Apache-2.0 | `b8e53f1` (2026-10-09) | none |
| Third-party picks (`pitch-craft`, `storytelling-with-data`, `modern-web-guidance`, `humanizer`, `logo-design`, `fixing-motion-performance`) | see each folder | see `VENDORED.md` in each folder | see `VENDORED.md` |
| own skills | — | — | — |

To update a vendored skill: clone the upstream into a temp folder, diff against the local folder,
re-apply the local edits listed above, update this table, run `bash .claude/scripts/sync-agents.sh`.
Keep only shared invocation policy in `agents/openai.yaml`; mirror the manual flag in SKILL.md.
Avoid extra UI metadata and duplicated instructions. The `grill-me` wrapper was removed; use `grilling`
for an interview or explicit `grill-with-docs` for the document-producing variant.
