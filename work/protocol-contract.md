# Backend–plugin contract v2

Owner: lead. Both workers read it and do not edit it; change requests go to the lead in the final report.
Source plan: `work/agent-plan.md`.

## Path ownership

| Worker | Owns |
|---|---|
| backend | `backend/**`, `docker-compose.yml`, `docker-bake.hcl`, `.env.example` |
| plugin | `plugin/Brim/**`, `plugin/tests/**`, `plugin/README.md` |
| lead | `docs/**`, `context/**`, `work/**`, root files |

## Transport

- HTTP API: `/api/v1`, JSON, header `Authorization: Bearer <instance token>`.
- WebSocket: plugin dials `GET /api/v1/instances/ws?token=<token>`; every frame is one JSON object.
- Local: plugin also serves MCP over HTTP on `127.0.0.1:<port>` (`initialize`, `tools/list`, `tools/call`)
  using the same dispatcher as the WebSocket bridge.
- Contract version constant `CONTRACT_VERSION = "2"`; plugin sends it in `hello`, backend rejects mismatch.

## WebSocket frames

Every frame: `{"type": str, "id": str, ...}`.

Plugin → backend:

| type | fields |
|---|---|
| `hello` | `contract_version`, `scene_epoch` (UUID per plugin process), `instance_id`, `slicer_version`, `modes` (list), `printer` |
| `state_snapshot` | `scene_epoch`, `scene_version` (int), `state` (object: printer, materials, profile, overrides, objects[], slice_state, errors[], settings[] — `{category, settings: [line]}`, only in snapshots) |
| `chat_message` | `conversation_id`, `text`, `attachment_ids` |
| `tool_result` | `call_id`, `run_id`, `ok` (bool), `scene_epoch`, `scene_version`, `result` (object), `error` (`{code, message}` or null), `applied` (list of completed ops) |
| `progress` | `call_id`, `stage`, `fraction` |
| `mcp_response` | `jsonrpc` envelope answering a backend `mcp_request` |
| `pending_calls` | on reconnect: `call_ids` still unfinished on plugin side |

Backend → plugin:

| type | fields |
|---|---|
| `hello_ack` | `instance_id`, `pending_calls` (call ids backend considers unfinished) |
| `tool_call` | `call_id`, `run_id`, `tool`, `arguments`, `expected_scene_epoch`, `expected_scene_version` |
| `chat_event` | `conversation_id`, `event` (`assistant_message`, `question`, `confirmation_request`, `tool_started`, `tool_finished`, `run_state`, `error`), `payload` |
| `mcp_request` | JSON-RPC 2.0 request |
| `cancel_run` | `run_id` |

Rules: a repeated `tool_call` with a known `call_id` returns the stored result and never reapplies it.
If either `expected_scene_epoch` or `expected_scene_version` differs from the plugin's, plugin answers `ok=false`, `error.code="stale_scene"`,
and no change is made. A partially executed batch stops at the failing op and reports `applied`.
Unknown outcome is reported as `error.code="outcome_unknown"`.

## HTTP endpoints (backend)

| Method path | Purpose |
|---|---|
| `POST /instances/register` | body `{instance_id}` → `{token}`; token creation for a new slicer instance |
| `GET/POST /conversations`, `GET /conversations/{id}` | list, create, read with messages and runtime (latest run, pending question/confirmation, tool events, saved result) |
| `POST /conversations/{id}/messages` | `{text, attachment_ids, mode}` starts or continues a run |
| `POST /attachments` | multipart upload, returns `{id, name, content_type, size, sha256}` |
| `GET /attachments/{id}` | download |
| `PUT /conversations/{id}/mode` | `{mode: "auto" | "ask"}` |
| `POST /runs/{id}/confirmation` | `{decision: "accept" | "reject" | "clarify", text?}` |
| `POST /runs/{id}/stop` | abort |
| `POST /runs/{id}/artifacts` | multipart chunked upload: `kind` (`gcode`/`3mf`), `scene_epoch`, `scene_version`, `chunk_index`, `chunk_count`, `sha256` |
| `GET /runs/{id}/artifacts/{kind}` | download |
| `GET /health` | existing |

LLM settings travel as `PUT /instances/llm` `{base_url, model, api_key}`: key kept in memory only, never logged
or persisted in history.

## Tool definitions (single source: backend `domain`, mirrored in `plugin/Brim/protocol/tools.json`)

`apply_changes(operations[])`, `search_settings(query)`, `inspect_profile()`, `inspect_material(material_id?)`,
`analyze_geometry(object_ids[], direction?)`, `render_scene(view)`, `slice()`, `ask_user(questions[])`.
Operation kinds in `apply_changes`: `select_mode`, `select_profile`, `select_material`, `set_global_setting`,
`set_extruder_setting`, `reset_overrides`, `import_model`, `open_3mf` (`restore_project` | `import_geometry`),
`transform` (absolute `position_mm`, `rotation_deg`, `scale`, `frame`, `rotation_center`), `duplicate`,
`arrange`, `delete`, `save_profile`.
The backend owns `tools.json`; the plugin copies it into `plugin/Brim/protocol/tools.json` unchanged.

## Recovery and ordering in v2

The instance token survives plugin restarts; `scene_epoch` does not. A new epoch resets the server's
scene counter and snapshot, but never deletes history or files. Batches, calls, snapshots, chunks and
artifacts retain their epoch. Legacy rows use an empty epoch and cannot authorize current edits.
Backend and plugin must upgrade together; v1 connections are rejected.

On every connection the plugin waits for `hello_ack`, sends a snapshot, reconciles pending calls and
resends LLM configuration. The backend resumes only after all three inputs are present. Until then,
runs keep their current state. An unknown execution outcome requests user assistance instead of
repeating a mutation. The plugin never repeats an already journaled call.

`GET /conversations/{id}` returns `runtime`: `run_id`, `state`, `pending`, `result`, `last_error`,
`events`. Each event has the same fields as a live chat event, including `event_id`. The read uses a
consistent database snapshot. The UI buffers events during the request and replays unseen events
after restoring the snapshot. Confirmation cards are actionable only for the current `batch_id`.

The scene includes `available_materials` with compatible root IDs, extruders and metadata.
`inspect_material(material_id)` also accepts inactive compatible materials; omitting the ID inspects
active materials. The LLM chooses materials from these facts.

After executing a tool, the plugin sends an atomic scene snapshot before its tool result.
A successful slice result retains the epoch/version of its exported files even if the scene changes
before delivery; the backend compares that revision with the current snapshot before completion.
