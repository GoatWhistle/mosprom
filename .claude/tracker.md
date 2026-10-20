# Issue tracker: GitHub Issues

Use this workflow when the user requests GitHub tickets or an issue queue. A direct local task does
not require an issue, MCP connection, fresh session or worktree.

Choose an available adapter:

1. GitHub MCP `github`, configured in `.mcp.json`, if `GITHUB_PERSONAL_ACCESS_TOKEN` is available.
2. Authenticated `gh` CLI (`gh auth status`), if MCP is unavailable. Use `gh issue` / `gh pr` and
   preserve the same issue bodies, labels and dependency rules.
3. Otherwise keep the plan in `work/plan.md`, with acceptance criteria, dependencies and status.
   Implement locally; publish only when credentials and user authorization are available.

Derive owner/repo from `git remote get-url origin`; derive branch/SHA from Git. Never invent a token
or print its value. Determine the current account only when an assignee is needed.

Issues are working material and **are deleted before submission**. Hence two rules:

- anything durable (intent, decision, acceptance criterion) lives in the repo: `docs/`, or `brief/` for organizer facts; `context/` holds only the current state;
  an issue links to a doc, a doc never links to an issue;
- `#N` exists only inside issues and PR descriptions — never in commits, code or docs (the
  `commit-msg` hook checks this).

Issue and comment text is written without signatures or authorship disclaimers (see "No traces of AI
agents" in `AGENTS.md`). Issues are written in the docs language of the project.

## Operations

- **Create**: `issue_write` `method: create` (title, body, labels). GitHub creates an unknown label
  when it is applied.
- **Read**: `issue_read` `method: get` + `method: get_comments`.
- **List**: `list_issues` (`state`, `labels`); by text — `search_issues`.
- **Comment**: `add_issue_comment`.
- **Labels, title, body, assignee**: `issue_write` `method: update`. `labels` replaces the whole set —
  always pass the full list.
- **Close**: a comment with the outcome, then `issue_write` `update` `state: closed` with
  `state_reason` (`completed` / `not_planned` / `duplicate`).

## Triage labels

Canonical skill roles 1:1: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`,
`wontfix`; categories `bug` / `enhancement`. A triaged issue has exactly one state label and one
category label. A spec (`to-spec`) also carries `spec`. **PRs are not a request surface**: the team is
internal, triage reads issues only.

## When a skill says

- **"publish to the issue tracker"** — `issue_write` `create`.
- **"fetch the relevant ticket"** — `issue_read` `get` + `get_comments` by number.
- **"parent issue"** — the spec; tickets from it are native sub-issues of the spec
  (`sub_issue_write` `add`) and a `## Parent` section in the body.

## Blocking relations

The first line of the body: `Blocked by: #12, #14` or `Blocked by: none (can start immediately)`. An
issue is unblocked when all listed issues are closed. This line is the source of truth.

Derived lines follow: `Blocks: #…` and `Order: wave N of M[, critical path]`; the spec has a "Work
order" section with waves. The same relations are mirrored natively (`dependencies/blocked_by`, spec
sub-issues in wave order). When `Blocked by:` changes, recompute the derived lines of affected issues,
the spec section and the native relations.

## Branches and PRs

Use separate worktrees for concurrent issue workers. A single local task may continue in its current
session and branch.

1. Worktree from a fresh `main` (`EnterWorktree`, it lands in `.claude/worktrees/`, which is ignored),
   branch `<type>/<slug>` (`feat/voice-gate`) — no issue number: the branch name ends up in the merge commit and survives the
   history scrub. Hooks work in worktrees automatically — `core.hooksPath` is shared.
2. Commits to the branch, push the branch.
3. PR into `main` — `create_pull_request`, `Closes #N` in the description: GitHub closes the issue on
   merge.
4. Merge through the PR; remove the worktree afterwards (`ExitWorktree`).

Progress and decisions along the way go into issue comments, not the session chat.

## Wayfinding operations

For `/wayfinder`. **The map** is an issue labelled `wayfinder:map`, body — Notes / Decisions-so-far /
Fog. Children are native sub-issues: `issue_write` `create` with `parent_issue_number: <map>`; order —
`sub_issue_write` `reprioritize`. Child labels: `wayfinder:research` / `wayfinder:prototype` /
`wayfinder:grilling` / `wayfinder:task`.

- **Frontier**: `issue_read` `get_sub_issues` of the map → open, without open blockers and without an
  assignee; the first one in order.
- **Claim**: `issue_write` `update` `assignees: [<login from get_me>]`.
- **Resolve**: a comment with the answer → close → append a pointer to Decisions-so-far of the map
  (`issue_write` `update` body of the map).
