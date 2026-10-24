# Backend HTTP contract

Read before changing routes, request mapping, errors or authentication. Public reference:
`docs/api.md`. Layer ownership follows [ARCHITECTURE.md](ARCHITECTURE.md).

## Implemented routes

| Route | Contract |
|---|---|
| `POST /v1/chat/completions` | Bearer OAuth token, JSON body mapped by `CompletionService`, one complete JSON response |
| `GET /v1/models` | Public list containing the fixed model `opus` |
| `GET /api/v1/health` | Public process liveness, without paid upstream calls |
| `/openapi.json`, `/docs` | Generated FastAPI schema and Swagger |

The requested model name is currently ignored: `MODEL = "opus"`. Streaming, token usage accounting
and general OpenAI parameter compatibility are not implemented. Additional generation parameters
must not be documented as supported without code and tests.

Messages support system/user/assistant/tool, text and base64 data URL images. Remote image URLs are
rejected. Tool definitions use function name/description/parameters; tool calls carry arguments as
JSON text in responses. Full behavior lives in `usecase/completion.py` and adapter transcript code.

## Authentication and data flow

The Bearer token is passed only to Claude. There are no application users, sessions or stored chat
records. Never log the token or body. The optional mirror uses its own configured key and receives
a copy of the validated body, with model replaced and stream disabled. Its result cannot control
the main answer. Preserve isolation tests when changing this path.

## Errors

Return `{code, message}` consistently through `controller/errors.py`:

- 401: missing/empty Bearer token.
- 422: invalid JSON body, roles, messages, tools or image encoding.
- 503: SDK absent, upstream failure/timeout or malformed model output.
- 500: unexpected or unmapped server error.

Keep internal exception details out of 5xx responses. Provider diagnostics go through the Logger
port with safe fields. Do not convert provider failure into a successful synthetic chat response.

## Validation and completion

Controller code owns HTTP extraction; CompletionService validates the generic JSON shape and maps
it to domain values. The current OpenAPI body is generic JSON, not a full Chat Completions schema.
If explicit schemas are introduced, keep them in controller and preserve domain independence.

After changing a contract, update `docs/api.md`, plugin consumers and affected tests together.
There is no standalone frontend or generated TypeScript client to rebuild. Done means the documented
request, success and error examples match implemented behavior and the relevant checks pass.
