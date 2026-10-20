---
name: submission
description: "Prepare final submission: platform fields, version consistency, fresh-clone checks, secrets review and cleanup."
disable-model-invocation: true
---

The jury sees only what was submitted, from a clean machine, possibly offline. Everything here checks that experience, not our working copy.

## 1. Freeze and version

- Feature freeze is announced; only fixes to the P0 scenario go in.
- One version: the service, the code, the deck and the video describe the same build. Tag it (`git tag submission-<n>`) and put the short SHA into `context/README.md`.

## 2. Walk the platform checklist

Open `brief/PLATFORM.md` and turn every requirement into a row: requirement, artifact, status, proof. Typical rows: repository with README and run instructions, the repository About (description, homepage, topics; skill `repo-meta`), deck PDF under the size limit, video within duration and resolution with voice, live URL and demo account, required docs. A row without proof is not done.

## 3. Product surfaces

- README in its product phase — `readme` skill.
- Docs pass, one file at a time — `docs-writing` skill (audit section). `docs/for-jury.md` route matches the e2e test and the live stand — `jury-route` skill.
- Deck and speech audited — `presentation/` skills `deck-audit` and `speaker-script`; PDF exported from the final deck.
- Limitations are stated first and match reality.
- No product file links into `brief/`, `context/`, `work/`, `.claude/` or any `AGENTS.md`: those disappear in the scrub.

## 4. Run it like the jury

On a clean directory (ideally another machine), with no `.env`:

```bash
git clone <repo> fresh && cd fresh
docker buildx bake
docker compose up
```

Then: seed demo data, walk the jury route, open the deck, play the video. Repeat once with the network off: fonts load, no CDN calls, no paid API is required, the LLM fallback works. Fix and retag if anything fails.

## 5. Secrets and licences

- `git grep -nE '(api[_-]?key|secret|token|password)\s*[:=]\s*\S{8,}'` over the tree and `git log -p` for anything that was committed and removed; rotate every leaked key, do not just delete it.
- `.env` files are not tracked; `.env.example` holds placeholders only.
- `LICENSE` has the team name; `docs/dependencies.md` lists versions and licences when the task asks.

## 6. Scrub and publish

1. Extra paths that must not ship (internal plans, rehearsal notes) go into `.claude/scrub-paths`, one per line.
2. `bash .claude/scripts/scrub-history.sh` → a bare repo in a temp dir. If it stops on a commit subject, add `old<TAB>new` to `.claude/scrub-subjects.tsv` and rerun. If it reports traces in content, fix them in the working repo with a commit and rerun.
3. Show the user the push commands it prints; the user pushes. If the old repo had PRs, push into a new empty repository.
4. Clone the published repo fresh and repeat step 4 against it.

## 7. Clean the defense machine

The laptop that shows the demo must hold no agent files either: an open IDE or terminal is part of
the show.

1. Best: run the demo from a fresh clone of the published, scrubbed repository.
2. Otherwise, in the working copy: commit everything, then `bash .claude/scripts/strip-ai.sh`
   (dry run: removals, edits, any trace or broken link that would remain, and the history report).
   Fix every reported line with a commit, then `bash .claude/scripts/strip-ai.sh --apply` for the
   files only, or `--apply --history` to also rewrite the whole history in place (subjects only,
   no co-authors, agent authors reassigned, agent files removed from every commit). Both write a
   backup first and print the restore command; `--history` leaves the force-push to the user.
   Internal docs that must not ship are listed in `.claude/scrub-paths` (globs allowed).
3. Run the demo once after the cleanup: `docker buildx bake && docker compose up`, the jury route, the deck.

## 8. Submit

Fill the platform forms (`submission-texts` skill in `presentation/` for character-limited fields), attach the PDF and the video, and screenshot the confirmation into `work/submission/` with the time.

Done: every `PLATFORM.md` row has proof, the published repo passes a fresh-clone run, and the confirmation is saved before the deadline.
