---
name: orchestrate-issues
description: "Run an explicitly requested GitHub issue queue with workers in separate worktrees and declared dependencies."
argument-hint: "<issue numbers>"
disable-model-invocation: true
---

You are the **orchestrator**: build a queue from the named issues and drive workers through the shell until the final report. You do not write code and do not merge PRs yourself.

The run is **autonomous**: ask the user nothing and wait for nothing — decide whatever needs a decision and record it in the issue or in the report. Workers behave the same way: a question becomes an issue comment with options, the worker takes the recommended one and continues.

The issue set is only the explicitly named one (argument or numbers in the request). No numbers — answer with one line "name the issues" and stop.

Tracker, operations and labels: `.claude/tracker.md`, relative to the repository root. Owner and repo come from `git remote get-url origin`; below they are `<owner>` and `<repo>`.

## Steps

1. **Collect.** For each number — `issue_read` `get` and `get_comments`.
   Done: every issue has its body and all comments read.

2. **Filter.** Drop closed issues and those whose `Blocked by:` points to an open issue outside the set. State labels and unanswered questions do not filter.

3. **Parts.** If the comments decided to ship an issue as several sequential PRs, each part is its own step with its own slug and a part line: `Part K: <what from the comment>, Refs #N in the PR`; the last one gets `Closes #N`.

4. **Steps.** Order is topological by `Blocked by:`. Within that:
   - issues whose bodies or briefs name shared files or modules go to different steps;
   - issues without overlaps run in parallel within one step;
   - an issue that replaces a mechanism others rely on goes before them;
   - short bug fixes go to the first step.
   Slug is latin from the title, without the number: the branch name `<type>/<slug>` survives the history scrub.
   Done: issues of one step share no files.

5. **Plan.** A table step → issue → slug → part → why here, plus the filtered issues with reasons. Into the chat and into `.claude/worktrees/logs/plan.md`, then straight to step 6.

6. **Run a step.** For every issue of the step — a separate Bash call with `run_in_background` (a worker runs longer than the Bash limit):
   ```bash
   bash skills/orchestrate-issues/run-worker.sh <N> <slug> ["<part line>"]
   ```
   The script creates worktree `.claude/worktrees/<slug>` from `origin/main` (or continues in an existing one) and logs to `.claude/worktrees/logs/<slug>.log`. Wait for notifications from all workers of the step.

7. **Outcome per issue** — from GitHub, not from the log: `list_pull_requests` with `head: <owner>:<type>/<slug>`, `state: all`.
   - PR merged — `git worktree remove .claude/worktrees/<slug>`, `git branch -D <type>/<slug>`.
   - PR open or no PR — one rerun of the same `run-worker.sh` with the same arguments. Still not merged — an issue comment with the reason from the log tail and a link to the PR. Issues depending on it via `Blocked by:` (transitively) drop out of the queue; other steps continue, the worktree stays.
   Done: every issue of the step is "merged" or "failed" with a comment.

8. **Report.** A table step → issue → outcome → PR. Separately — questions workers resolved by recommendation without an answer (links to comments), so the user can revisit them, and the remaining worktrees.

A rerun on the same set continues: closed issues drop out at step 2, existing worktrees are reused.
