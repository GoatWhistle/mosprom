---
name: compact-context
description: "Use when context checks report overflow, missing required files or extra files; preserve explicit user instructions."
---

`context/` is the working memory every session loads in full, so it holds only the current state and
links to everything else. Compacting is **promotion and deletion**: each entry either moves to the
place that owns it or is deleted because git and its evidence already hold it. A summary that drops a
number, a date, a link or the user's words loses them silently, so text is shortened only by moving its
detail behind a link.

## 1. Measure

Run `python3 .claude/scripts/context_budget.py`. Note mutable overflow, missing required files and files outside the three allowed ones. Restore missing
files with their known state, or empty template fields when no state is available; preserve user instructions.

Done: you have the list of offending files with their character counts.

## 2. Move foreign files out

Every file in `context/` other than `README.md`, `SESSION.md` and `open-questions.md` moves by kind:

| Kind | Goes to |
|---|---|
| Organizer text: task, answers, rules, chat exports, originals | `brief/` (see `brief/README.md`) |
| A skill's working output: naming, brand, design, competitors, repo meta | `work/` (see `work/README.md`) |
| A decision, a measured result, a limitation | `docs/adr/`, `docs/evidence.md`, `docs/limitations.md` |

Fix every link to the moved file (`rg '<old path>'`).

Done: `context/` holds the three files and nothing else.

## 3. Promote or delete, entry by entry

Go through each over-budget file one entry at a time and apply the first rule that matches:

| Entry | Action |
|---|---|
| A user instruction in `SESSION.md` | Keep it word for word. Remove only when the user withdrew it |
| An organizer answer or fact | Verbatim into `brief/QA.md` or `brief/event.md` with source and date, then delete here |
| A decision that is not reopened | An ADR in `docs/adr/`, linked from project rules if it constrains future work, then delete here |
| A measured or verified claim | A row in `docs/evidence.md`; Current facts keeps one row and the link |
| A closed question | The answer to `brief/QA.md`, the row deleted from `open-questions.md` |
| An assumption the jury sees | The assumptions section of `docs/requirements-map.md`, the row kept until answered |
| A finished item in «Done», a fixed pitfall, a superseded entry | Delete: git and the linked evidence keep it |
| A live entry that is too long | Its detail moves to `work/` or `docs/`; the entry becomes one or two sentences and the link |

Numbers, dates, links and quoted words survive every move unchanged.

Done: every entry has been kept, moved with a link left behind, or deleted, and nothing was reworded
in place to make it shorter.

## 4. Verify

Rerun `python3 .claude/scripts/context_budget.py`. It passes and mutable content sits at or below 80% of
its budget. Protected user instructions may exceed the SESSION target: retain them, report the
notice and continue; repeated compaction cannot shorten them. Restore any missing required file.
Run `rg 'context/' docs README.md` to
confirm no product file links into `context/`.

Done: the check passes with that margin and no link points at a moved or deleted entry.

## 5. Report

Tell the user in a few lines what moved where and how many entries were deleted, with the new counts
from the check.
