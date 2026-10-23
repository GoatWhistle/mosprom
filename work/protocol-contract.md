# Backend–plugin contract v1

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
- Contract version constant `CONTRACT_VERSION = "1"`; plugin sends it in `hello`, backend rejects mismatch.

## WebSocket frames

Every frame: `{"type": str, "id": str, ...}`.

Plugin → backend:

| type | fields |
|---|---|
| `hello` | `contract_version`, `instance_id`, `slicer_version`, `modes` (list), `printer` |
| `state_snapshot` | `scene_version` (int), `state` (object: printer, materials, profile, overrides, objects[], slice_state, errors[]) |
| `chat_message` | `conversation_id`, `text`, `attachment_ids` |
| `tool_result` | `call_id`, `run_id`, `ok` (bool), `scene_version`, `result` (object), `error` (`{code, message}` or null), `applied` (list of completed ops) |
| `progress` | `call_id`, `stage`, `fraction` |
| `mcp_response` | `jsonrpc` envelope answering a backend `mcp_request` |
| `pending_calls` | on reconnect: `call_ids` still unfinished on plugin side |

Backend → plugin:

| type | fields |
|---|---|
| `hello_ack` | `instance_id`, `pending_calls` (call ids backend considers unfinished) |
| `tool_call` | `call_id`, `run_id`, `tool`, `arguments`, `expected_scene_version` |
| `chat_event` | `conversation_id`, `event` (`assistant_message`, `question`, `confirmation_request`, `tool_started`, `tool_finished`, `run_state`, `error`), `payload` |
| `mcp_request` | JSON-RPC 2.0 request |
| `cancel_run` | `run_id` |

Rules: a repeated `tool_call` with a known `call_id` returns the stored result and never reapplies it.
If `expected_scene_version` differs from the plugin's, plugin answers `ok=false`, `error.code="stale_scene"`,
and no change is made. A partially executed batch stops at the failing op and reports `applied`.
Unknown outcome is reported as `error.code="outcome_unknown"`.

## HTTP endpoints (backend)

| Method path | Purpose |
|---|---|
| `POST /instances/register` | body `{instance_id}` → `{token}`; token creation for a new slicer instance |
| `GET/POST /conversations`, `GET /conversations/{id}` | list, create, read with messages |
| `POST /conversations/{id}/messages` | `{text, attachment_ids, mode}` starts or continues a run |
| `POST /attachments` | multipart upload, returns `{id, name, type, size, sha256}` |
| `GET /attachments/{id}` | download |
| `PUT /conversations/{id}/mode` | `{mode: "auto" | "ask"}` |
| `POST /runs/{id}/confirmation` | `{decision: "accept" | "reject" | "clarify", text?}` |
| `POST /runs/{id}/stop` | abort |
| `POST /runs/{id}/artifacts` | multipart chunked upload: `kind` (`gcode`/`3mf`), `scene_version`, `chunk_index`, `chunk_count`, `sha256` |
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
