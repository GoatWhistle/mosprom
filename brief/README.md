# Brief

Everything the organizers gave us, kept verbatim: the task, their answers, the platform rules, the
event itself and the chats. This folder is the ground truth the rest of the repo cites. It is read on
demand, by pointer, never loaded whole into a session.

Scrubbed at submission together with `context/` and `work/`. No product file links here; product docs
cite «ТЗ, раздел X, с. N».

## What is where

| Need | File |
|---|---|
| The task statement verbatim, with pages | [TASK.md](TASK.md) |
| Organizer answers verbatim, with source and date | [QA.md](QA.md) |
| What the submission platform requires, limits, deadlines | [PLATFORM.md](PLATFORM.md) |
| Requirements, jury criteria and weights, timeline, bonuses | [requirements.md](requirements.md) |
| The hackathon, the track, organizers, people, channels, schedule | [event.md](event.md) |
| Organizer and team chat exports, by channel and day | [chats/](chats/README.md) |
| Original files and their checksums | [sources/README.md](sources/README.md) |

## Rules

- **Preserve sources.** Originals, `TASK.md`, `QA.md` and chat exports are append-only, except corrections checked against their source. Preserve page markers, quotes and timestamps.
- **Update derived views.** `requirements.md` and `event.md` may be reorganized as the brief changes; every fact keeps its source, and our assumptions remain labelled.
- **Verbatim over retelling.** `TASK.md`, `QA.md` and `chats/` hold the source text with its page,
  author and timestamp. `requirements.md` is the one retelling, and every line in it carries its page.
- **Precedence:** the original file in `sources/` wins over `QA.md`, `QA.md` wins over
  `requirements.md`. A newer official document overrides an older answer; note it next to the answer.
- **Our ideas are marked** «**наше:**». An unmarked line here reads as an organizer requirement.
- **New material arrives:** the original goes to `sources/` with a checksum row, its text to the file
  it belongs to, and anything that changes our plan becomes one line in
  [`context/README.md`](../context/README.md) «Current facts».
