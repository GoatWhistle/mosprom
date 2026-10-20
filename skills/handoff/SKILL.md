---
name: handoff
description: "Save the current task, explicit instructions and next actions to context/SESSION.md for another session."
argument-hint: "What will the next session be used for?"
disable-model-invocation: true
---

Update `context/SESSION.md` in the repository so a fresh session can continue without the chat.

1. Preserve active explicit user instructions word for word, including dates and constraints.
2. Read the actual branch and SHA with Git. Record the current task, what runs, the next actions in
   order, unresolved pitfalls and failed checks with their commands.
3. Link existing specs, plans, ADRs and evidence rather than copying them. Put long working detail in
   `work/handoff.md` and leave a short pointer in SESSION.
4. Name only skills relevant to the next actions. If arguments were supplied, use them to focus the handoff.
5. Remove superseded session facts. Redact secrets. Run `python3 .claude/scripts/context_budget.py`;
   use `compact-context` for mutable overflow, preserving the protected instructions.

Done: the three context files describe the current state and point to the detail needed to resume.
