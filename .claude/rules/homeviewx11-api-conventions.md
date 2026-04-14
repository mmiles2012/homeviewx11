---
paths:
  - "server/api/**"
  - "server/main.py"
---

# API conventions — HomeView

## Route prefix

All REST endpoints live under `/api/v1/`. The WebSocket is at `/ws/control` (no
`/api/v1` prefix). New REST routes must use the `/api/v1/` prefix — do not add
routes at the root.

## Error response shape

Every error response — regardless of which layer raises it — must serialize to:

```json
{
  "error": {
    "code": "SNAKE_CASE_CODE",
    "message": "Human-readable description",
    "details": {}
  }
}
```

`code` is `SNAKE_CASE` (e.g., `INVALID_PAIRING_CODE`, `CELL_NOT_FOUND`). `details`
is an object — use `{}` when no structured details apply, never `null` or omit.

Do not return bare FastAPI `HTTPException(detail="...")` — wrap in the envelope.

## Dependency injection

Engine, source registry, preset manager, and auth are wired via
`server/api/dependencies.py` using FastAPI `Depends()`. In new routes, accept these
as `Depends(get_engine)` / `Depends(get_registry)` / etc. — never import singletons
directly in route handlers.

## Auth

All protected routes accept `Authorization: Bearer <token>`. The WebSocket
authenticates via `?token=` query param. The only public routes are:

- `GET /api/v1/server/health`
- `GET /api/v1/pair/code`
- `POST /api/v1/pair`

New routes default to protected — add the auth dependency unless the route is
explicitly public.

## Pydantic v2

Request and response models use Pydantic v2. Use `model_dump()` and
`model_validate()` — never `.dict()` or `.parse_obj()` (v1 API).

## State broadcasting

State-mutating routes must emit events via the `EventBus` so the WebSocket pushes
updates to connected clients. See how `CompositionEngine` callbacks are wired in
`server/main.py` — follow the same pattern for new state changes.
