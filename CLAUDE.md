# HomeView — Claude Instructions

## Project overview

HomeView is a self-hosted multi-stream video wall controller. It runs a FastAPI server that manages multiple Chromium subprocesses on a single X11 display, positioning them via python-xlib according to JSON layout definitions. Clients pair over HTTP (6-digit code → Bearer token) and control the display via REST + WebSocket.

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

All config via env vars or `.env` file with `HOMEVIEW_` prefix. Key vars:
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

**All tests use mock mode** — the test suite never spawns real Chromium or touches X11. The `conftest.py` wires up async fixtures and a mock app. Never set `HOMEVIEW_MOCK=0` in tests.

**Test files map 1:1 to modules** (e.g. `tests/test_engine.py` → `server/composition/engine.py`).

---

## Code conventions

- `from __future__ import annotations` in every module (deferred evaluation)
- Public functions: type hints required, modern syntax (`list[int]`, `str | None`)
- Pydantic v2 models throughout — use `model_dump()`, `model_validate()`, not `.dict()`/`.parse_obj()`
- Async/await everywhere in the server layer; sync only in layout/config utilities
- Error responses follow `{"error": {"code": "SNAKE_CASE", "message": "...", "details": {}}}` shape
- Route prefixes: all REST endpoints live under `/api/v1/`
- FastAPI `Depends()` for injecting engine/registry/preset manager — see `server/api/dependencies.py`

---

## Architecture notes

### CompositionEngine (`server/composition/engine.py`)

Central coordinator. Holds the current layout, list of `Cell` objects, and audio routing state. Emits state change events via registered callbacks (wired to `EventBus` → WebSocket in `main.py`).

Key methods: `start()`, `stop()`, `set_layout()`, `assign_source()`, `clear_cell()`, `get_state()`.

Background task `_geometry_enforcer` re-applies X11 window geometry every 5 s (handles windows that escape placement).

### Cell (`server/composition/cell.py`)

Wraps one Chromium subprocess. Status: `EMPTY → STARTING → RUNNING`. Uses `ChromiumLauncher` abstraction so tests inject `MockChromiumLauncher` instead of real subprocesses.

Chromium is launched in `--app=<url>` mode (NOT `--kiosk`) with a per-cell `--user-data-dir` profile.

### LayoutManager (`server/composition/layout.py`)

Loads `*.json` files from `layouts/`. Cell positions are proportional `[0,1]` — `compute_geometry()` converts to pixels at runtime. `compute_transition()` maps sources across layout changes by role priority (hero → side → grid → pip).

### Auth flow

1. On first boot, server generates a 6-digit code stored in `server_state` table (5 min TTL).
2. Client fetches `GET /api/v1/pair/code` and submits to `POST /api/v1/pair`.
3. On success, code is consumed and a Bearer token is issued (stored in `tokens` table).
4. All protected routes require `Authorization: Bearer <token>`.
5. WebSocket authenticates via `?token=` query param.

### Mock mode

`HOMEVIEW_MOCK=1` substitutes `MockChromiumLauncher` (fake PIDs, no subprocess) and `MockWindowManager` (no-op X11 calls). Display resolution defaults to 1920×1080. The entire API and WebSocket still function normally. Always use this for development and CI.

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

`role` values: `hero`, `side`, `grid`, `pip` — used for transition priority when switching layouts.

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
