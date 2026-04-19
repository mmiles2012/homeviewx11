# HomeView — Claude Instructions

## Project overview

Self-hosted multi-stream video wall controller. FastAPI server manages multiple Chromium subprocesses on single X11 display, positioned via python-xlib from JSON layout definitions. Clients pair over HTTP (6-digit code → Bearer token), control display via REST + WebSocket.

**Stack:** Python 3.12+, FastAPI, uvicorn, aiosqlite (SQLite), pydantic-settings, python-xlib

---

## Running the server

```bash
# Development (real X11 + Chromium required)
uv run homeview

# Development without X11/Chromium — full API still works
HOMEVIEW_MOCK=1 uv run homeview

# Reset pairing (revoke all tokens, print new code)
uv run homeview-reset-pairing
```

Config via env vars or `.env` with `HOMEVIEW_` prefix. Key vars:
- `HOMEVIEW_MOCK=1` — mock mode (no X11, no Chromium subprocesses)
- `HOMEVIEW_PORT=8000`, `HOMEVIEW_DISPLAY=:0`
- `HOMEVIEW_DB_PATH`, `HOMEVIEW_PROFILES_DIR`, `HOMEVIEW_LAYOUTS_DIR`

---

## Testing

```bash
uv run pytest -q                                    # full suite
uv run pytest -q --cov=server --cov-fail-under=80  # with coverage
uv run pytest tests/test_engine.py -q              # single file
```

All tests use mock mode — never spawn real Chromium or touch X11. `conftest.py` wires async fixtures + mock app. Never set `HOMEVIEW_MOCK=0` in tests.

Test files map 1:1 to modules (`tests/test_engine.py` → `server/composition/engine.py`).

---

## Code conventions

- `from __future__ import annotations` in every module
- Public functions: type hints required, modern syntax (`list[int]`, `str | None`)
- Pydantic v2: `model_dump()`, `model_validate()` — never `.dict()`/`.parse_obj()`
- Async/await throughout server layer; sync only in layout/config utilities
- Error responses: `{"error": {"code": "SNAKE_CASE", "message": "...", "details": {}}}`
- Route prefix: `/api/v1/` for all REST endpoints
- `FastAPI Depends()` for engine/registry/preset injection — see `server/api/dependencies.py`

---

## Architecture notes

### CompositionEngine (`server/composition/engine.py`)

Central coordinator. Holds current layout, `Cell` list, audio routing state. Emits state changes via callbacks (wired to `EventBus` → WebSocket in `main.py`).

Key methods: `start()`, `stop()`, `set_layout()`, `assign_source()`, `clear_cell()`, `get_state()`.

Background task `_geometry_enforcer` re-applies X11 geometry every 5 s.

### Cell (`server/composition/cell.py`)

Wraps one Chromium subprocess. Status: `EMPTY → STARTING → RUNNING`. Uses `ChromiumLauncher` abstraction — tests inject `MockChromiumLauncher`.

Chromium launched in `--app=<url>` mode (NOT `--kiosk`) with per-cell `--user-data-dir`.

### LayoutManager (`server/composition/layout.py`)

Loads `*.json` from `layouts/`. Cell positions proportional `[0,1]` — `compute_geometry()` converts to pixels. `compute_transition()` maps sources across layout changes by role priority (hero → side → grid → pip).

### Auth flow

1. First boot: server generates 6-digit code in `server_state` table (5 min TTL).
2. Client: `GET /api/v1/pair/code` → submit to `POST /api/v1/pair`.
3. Success: code consumed, Bearer token issued (stored in `tokens` table).
4. Protected routes require `Authorization: Bearer <token>`.
5. WebSocket authenticates via `?token=` query param.

### Mock mode

`HOMEVIEW_MOCK=1` substitutes `MockChromiumLauncher` (fake PIDs) + `MockWindowManager` (no-op X11). Display defaults to 1920×1080. Full API + WebSocket still function. Always use for dev and CI.

---

## Layout JSON schema

```json
{
  "id": "my_layout",
  "name": "My Layout",
  "gap_px": 4,
  "cells": [
    { "index": 0, "role": "hero", "x": 0.0, "y": 0.0, "w": 0.75, "h": 1.0 },
    { "index": 1, "role": "side", "x": 0.75, "y": 0.0, "w": 0.25, "h": 1.0 }
  ]
}
```

`role` values: `hero`, `side`, `grid`, `pip` — transition priority order.

---

## Key files

| File | Purpose |
|------|---------|
| `server/main.py` | App factory (`create_app`), lifespan, route wiring |
| `server/config.py` | All configuration (`Settings`, `get_config()`) |
| `server/models.py` | Pydantic domain models (`Source`, `CellState`, `Preset`, etc.) |
| `server/db.py` | aiosqlite helpers, schema init (`init_db`) |
| `server/api/routes.py` | All REST endpoints |
| `server/api/websocket.py` | `/ws/control` WebSocket handler |
| `server/composition/engine.py` | `CompositionEngine` — central coordinator |
| `server/composition/layout.py` | `LayoutManager`, geometry, transitions |
| `server/composition/cell.py` | `Cell`, `ChromiumLauncher` abstraction |
| `server/composition/window.py` | `WindowManager` (X11) |
| `server/auth/pairing.py` | 6-digit pairing code flow |
| `server/auth/tokens.py` | Bearer token issuance + validation |
| `layouts/*.json` | Built-in layout definitions |
| `tests/conftest.py` | Shared async fixtures, mock app factory |

---

## Quality checklist before marking work done

- [ ] `uv run pytest -q` — 0 failures
- [ ] `ruff format .` — no changes
- [ ] `ruff check .` — clean
- [ ] New logic has tests; mocks cover all subprocess/X11/DB calls in unit tests
- [ ] API responses follow `{"error": {"code": ..., "message": ...}}` error shape
- [ ] `HOMEVIEW_MOCK=1` still works after changes to composition layer
