# Plugin contract v3: OpenAI chat completions + MCP

Replaces contract v2 (backend agent, WebSocket bridge, ledger, scene epochs) on 2026-10-23.
Decision: `docs/adr/0002-plugin-agent-openai-mcp-host.md`. Plan: `~/.claude/plans/misty-honking-crescent.md`.

## Parts

| Part | Role |
|---|---|
| `plugin/Brim/agent/loop.py` | Agent loop in a background thread; one turn at a time |
| `plugin/Brim/agent/llm_client.py` | `POST {base_url}/chat/completions`, `GET {base_url}/models`, urllib, no streaming |
| `plugin/Brim/agent/hub.py` | Merges tools of the built-in server and user servers; routes calls |
| `plugin/Brim/agent/mcp_client.py` | Streamable HTTP client: JSON or SSE replies, `Mcp-Session-Id`, re-initialize on 404 |
| `plugin/Brim/protocol/{mcp,local_mcp}.py` | Built-in MCP dispatcher; also served on `127.0.0.1:<port>/mcp` with a token |
| `backend` `/v1/chat/completions` | Optional stateless proxy to Claude Agent SDK; Bearer = Claude OAuth token |

## Model request

- `messages[0]` is `system`: prompt from `agent/prompts.py` plus scene context JSON and the settings
  digest, rebuilt every step and never stored.
- History is stored OpenAI messages. Private keys start with `brim_` and are stripped before sending:
  `brim_attachments`, `brim_images` (paths → `image_url` data URLs on user messages), `brim_hidden`,
  `brim_tool`, `brim_server`, `brim_status` (`ok`, `failed`, `rejected`, `skipped`, `running`).
- Tool images go into one hidden user message after all tool results of the step.
- Tools: built-in names unprefixed; external `<server>__<tool>` sanitised to `[a-zA-Z0-9_-]{1,64}`;
  plus `ask_user {questions: [{text, options?}]}` which is not an MCP tool.

## Turn rules

- A reply without `tool_calls` ends the turn; limit 40 steps.
- `ask_user` ends the turn; the pending question is the last `ask_user` call without a result. The
  answer starts a new turn and becomes `{"answer": text}`. Any other new message first closes dangling
  calls with `not_answered` / `not_executed`.
- Before a tool runs, a placeholder result `interrupted` (`brim_status: running`) is saved, then
  replaced by the real result.
- Confirmation (`agent/confirmation.py`): ask mode — every `apply_changes`, `slice` and external tool
  without `readOnlyHint`; auto mode — setting outside min/max or warning bounds or changed more than
  ×`risk_ratio` (default 2), and external tools with `destructiveHint`. Rejection result:
  `rejected_by_user` with the user's comment.
- Cancel: released immediately while waiting for the model or a decision (late model reply is
  discarded); during a tool the executor is cancelled and the UI waits for the thread.

## Built-in tools

`search_settings`, `inspect_profile`, `inspect_material`, `inspect_scene`, `analyze_geometry`,
`render_scene` (text + PNG image block), `apply_changes` (`import_model` / `open_3mf` take a local
`path`), `slice` (writes `result.gcode` and `result.3mf` into `chats/<id>/output/`). Result text is
JSON `{ok, result, error, applied}`; `isError` mirrors `ok`.

## Storage

`<data>/brim/chats/<id>/chat.json` (`id`, `title`, `mode`, `created_at`, `updated_at`, `messages`),
`scene.3mf`, `files/`, `output/`; `chats/index.json` keeps `active` and scene state per chat.
