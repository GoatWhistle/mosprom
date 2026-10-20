# Chats

Exports of organizer and team chats, verbatim, so an answer given in a chat can be quoted with its
author and time instead of being remembered.

## Layout

One folder per channel, one file per day: `chats/<channel>/<YYYY-MM-DD>.md`. The channel name is the
kebab-case name from the channel table in [event.md](../event.md).

Each message is one block:

```markdown
### HH:MM, {{author}} ({{role: organizer, expert, team}})

> {{message verbatim, with typos}}
```

## Rules

- Export, never paraphrase. Media gets a line with its file name in `../sources/` and, for voice or
  video, the transcript below it.
- An organizer answer that changes the task is copied verbatim into [QA.md](../QA.md) with a link to
  its chat file and time; the chat file stays as the source.
- Team chats go here only when they hold a decision the user wants kept; the decision itself goes to
  `docs/adr/` or `AGENTS.md` «Decisions that are not reopened».
