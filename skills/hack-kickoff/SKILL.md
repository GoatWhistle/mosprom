---
name: hack-kickoff
description: "Use when starting a hackathon or processing a changed organizer brief; establish criteria, thesis, P0 and timeline."
---

Kickoff turns a pile of organizer material into a plan the whole team and every agent can act on. Nothing gets built until steps 1–5 are done; a wrong reading of the task costs more than any bug.

## 1. Ingest the sources

- Put every original file into `brief/sources/` and record its SHA-256 and page count in `brief/sources/README.md`.
- `brief/TASK.md` — the task statement verbatim with page markers (`[с. N]` for a Russian source, `[p. N]` for an English one). No retelling here.
- `brief/QA.md` — organizer answers verbatim with source and date (chat, call, FAQ). Later official files win over earlier answers; say so next to the entry.
- `brief/PLATFORM.md` — submission rules: what is submitted (repo, PDF, video, live URL, demo account, docs), limits (size, duration, resolution, characters), deadlines with timezone, "one version" rules, anything that disqualifies.
- `brief/event.md` — the hackathon, the track, organizers and experts, channels, schedule, team; chat exports go to `brief/chats/` (see `brief/chats/README.md`).

Done: every requirement in the task has a page reference and no source file is left unread.

## 2. Requirements and criteria

Write `brief/requirements.md`:

- a retelling of every requirement with its page, split into mandatory / optional / bonus;
- the jury criteria table: criterion, weight, what evidence would max it, which artifact shows it (stand, code, deck, docs, video);
- the timeline by day with checkpoints and mandatory intermediate pitches;
- the documentation the task explicitly asks for (it becomes rows in `docs/README.md`).

Unknown weights are quoted verbatim from the source and marked as unweighted. Ambiguities go to `context/open-questions.md` (question, why it changes our plan, where to get the answer) and are sent to organizers on day one.

Done: each criterion maps to at least one planned artifact.

## 3. Thesis and the P0 scenario

Decide together with the user, then write down:

- **Positioning in one line** and the core promise (a contrast or a negation reads strongest: "X, which cannot be Y").
- **The P0 scenario**: the end-to-end path the jury will click, step by step, with the moment that proves the promise. This is also the future `docs/for-jury.md` route and the e2e test.
- **Three solutions** — the three mechanisms that make it work; they become README "Три решения" and the key-mechanics slides.
- **What will be measured**: metric, baseline, method, sample, threshold. Write the skeleton of `docs/validation-plan.md` now; the plan is fixed before any run.
- **What we will not do** — explicit out-of-scope list.

Stress-test the thesis with the `grilling` skill when the user agrees. Done: the P0 scenario fits on one screen and every step names the criterion it serves.

## 4. Fill the agent context

- Root `AGENTS.md`: replace the header placeholders, write project decisions in `docs/adr/` and link them (stack, contract source, LLM fallback, data, auth or no auth, offline demo), set the deadline.
- `context/README.md`: first dated row in "Current facts"; `context/SESSION.md`: the user's instructions so far. Both stay within the budget (`python3 .claude/scripts/context_budget.py`).
- Domain words go to `docs/glossary.md` through the `domain-modeling` skill.

## 5. Plan the work

- Write the P0 plan in `work/plan.md` with acceptance criteria, dependencies and ownership. If the user requests tickets, use explicit `to-spec` / `to-tickets` through an adapter from `.claude/tracker.md`.
- Streams and ownership: who owns backend, frontend, defense; which shared files have one owner; the contract (OpenAPI shape, seed data, token names) is committed first; the backend ships each endpoint thin but real before the screen that needs it, and nobody bridges a gap with mocks.
- Order by criteria weight; P0 before anything else.

## 6. Name, brand and look

Run `naming`; then `refero-style`: the user picks a style on <https://styles.refero.design/> and the agent maps it onto the tokens (the agent never picks the style); then `brand-identity` for the mark; then `frontend/PRODUCT.md` and `frontend/DESIGN.md`. A name and a mark on day one make the stand, the deck and the README feel like one product.

## 7. Timeline

Unless `PLATFORM.md` dictates otherwise, put these checkpoints into `brief/requirements.md` relative to the deadline T:

| When | What |
| --- | --- |
| End of day 1 | P0 path clickable end to end on the real backend with seeded data, name and tokens set |
| T − 24h | Feature freeze for P0/P1, measurements run, deck outline with real numbers |
| T − 8h | Docs pass, README product phase, deck content freeze |
| T − 4h | Backup demo recording, rehearsal with timer, `deck-audit` |
| T − 2h | Final checklist, history scrub, fresh-clone run; explicit `submission` workflow when requested |
| T − 1h | Submitted; the rest is buffer |

If an intermediate pitch is required, use the kickoff variant in `presentation/` (`pitch-deck` skill).

Done: `brief/` and `context/` have no placeholders left, `AGENTS.md` header is real, a plan or requested tickets cover the P0 scenario, and the user has confirmed the thesis.
