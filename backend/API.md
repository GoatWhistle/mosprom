# Backend HTTP contract

Read before changing routes, HTTP schemas, errors or authentication. Layer placement follows
[ARCHITECTURE.md](ARCHITECTURE.md).

## Request path

The controller validates request shape, obtains the authenticated actor from trusted server state,
maps input into a use case command and calls the use case. It maps the result or known business
failure into an explicit HTTP response. Business rules and access decisions execute in the use case
and domain even when the same action arrives through a worker or script.

- Keep Pydantic request/response schemas in `controller/`; use explicit response fields.
- Treat actor identity and permissions as server-owned. A submitted user ID or claimed role does
  not grant access.
- Check visibility before returning protected records; filter list and detail queries consistently.
  Establish the project's 403/404 policy and test it for every applicable action.
- Validate format, required fields and basic bounds at the HTTP edge. Business invariants remain
  authoritative in the core and cannot depend on Pydantic validation having run.
- Pagination, ordering, timestamp/timezone and identifier conventions are fixed for the project
  and recorded in product `docs/api.md`; new routes follow those conventions.

## Errors

Use one error envelope, including validation errors:

```json
{
  "code": "invalid_state_transition",
  "message": "The requested transition is unavailable"
}
```

`code` is a stable machine-readable `snake_case` identifier. `message` is safe English diagnostic
text; the frontend displays its own localized dictionary entry for the code. Domain/usecase
failures know no HTTP status; controller error mapping assigns it.

- Define statuses and error codes for each scenario in the generated contract and product docs.
- Convert known failures explicitly. Unexpected failures remain server errors and are logged safely;
  they are not reclassified as successful or user-caused results.
- Responses and logs never contain credentials, provider tokens, SQL traces or sensitive request
  bodies. Error mapping does not reveal records the actor cannot access.
- A failed mutation preserves state or rolls back its transaction. Partial success is explicit in
  the endpoint contract when the product requires it.

## OpenAPI and frontend types

- Generate OpenAPI from the implemented FastAPI routes and explicit schemas; serve `/openapi.json`.
- Document request, success and error schemas in route configuration. Do not hand-edit generated
  schemas or add code comments/docstrings to supply descriptions.
- Expose only implemented endpoints or a documented, honest unavailable response. A successful
  response comes from actual logic and storage.
- Regenerate frontend types with `cd frontend && npm run api:types` from the repository root whenever
  the public contract changes. Update consumers and `docs/api.md` in the same change.
- A breaking rollout follows: consumers accept both forms, backend changes, old form is removed.
  A coordinated first implementation may establish a single contract before any consumer ships.

## Health and configuration

- Implement `GET /api/v1/health` for the Compose healthcheck. Report the actual health policy;
  document whether it represents process liveness or dependency readiness.
- Configuration is validated at startup. Required capabilities fail with a safe, actionable error;
  optional paid providers use the configured deterministic implementation when no key is present.
- Construct clients and use cases in the composition root. Routers receive use cases through
  registered factories or providers, without creating database connections or SDK clients themselves.
