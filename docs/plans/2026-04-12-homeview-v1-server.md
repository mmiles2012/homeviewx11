# HomeView v1 Server-Side Implementation Plan

Created: 2026-04-12
Status: COMPLETE
Approved: Yes
Iterations: 0
Worktree: Yes
Type: Feature

## Summary

**Goal:** Implement the complete HomeView v1 server-side: composition engine, FastAPI control server, audio router, source registry, layout system, presets, interactive mode, and pairing/auth — all testable via API calls without a PWA frontend.

**Architecture:** A Python FastAPI server orchestrates a composition engine that manages Chromium cells positioned via python-xlib on X11. Audio routing uses pactl (PulseAudio-compatible). SQLite stores sources, presets, and auth tokens. A `--mock` mode stubs out X11/Chromium/pactl for development and testing.

**Tech Stack:** Python 3.12+, FastAPI + Uvicorn, python-xlib, SQLite (aiosqlite), pactl via subprocess, pytest + httpx for testing.

## Scope

### In Scope

- Project scaffolding (pyproject.toml, uv, directory structure)
- Configuration system with mock mode support
- SQLite database layer (sources, presets, auth tokens)
- Source registry with pre-loaded streaming sources + CRUD
- Layout system: JSON layout files, geometry computation, deterministic switching
- Composition engine: cell lifecycle, Chromium process management, window placement (python-xlib)
- Audio router: PulseAudio/PipeWire routing via pactl, PID-based sink-input matching
- Health monitoring: crash detection, exponential backoff restart, crash-loop protection
- FastAPI control server: all REST endpoints per PRD Section 5.5.1
- WebSocket: state.updated and cell.health events per PRD Section 5.5.2
- Pairing mode: 6-digit code generation, Bearer token issuance
- Preset system: save/load/apply current state
- Interactive mode: start/stop per cell
- Display detection via xrandr
- systemd service file
- Comprehensive test suite (unit + integration)

### Out of Scope

- Remote Control PWA (separate plan)
- HTTPS/TLS certificate generation (document as setup step)
- Pairing overlay on TV display (requires a display process — separate from server; `GET /api/v1/pair/code` substitutes for dev/testing)
- Sonos / wireless audio (v2)
- Multi-TV orchestration (v2)
- Automated "still watching" dismissal (v2+)

## Approach

**Chosen:** Bottom-up layered architecture

**Why:** Each layer (config → DB → models → engine → API) builds on the previous, making each task independently testable. Mock mode at the system boundary means the entire stack is testable without X11/Chromium/pactl.

**Alternatives considered:**
- **Top-down (API-first):** Start with API stubs, fill in engine later. Rejected: harder to test behavior without the engine working.
- **Monolithic:** Build everything in fewer, larger files. Rejected: harder to test, harder to parallelize future work.

## Context for Implementer

> This is a **greenfield project** — no existing code. The PRD at `docs/prd/2026-04-12-homeview-multi-stream-video-wall.md` is the sole requirements document.

- **Patterns to follow:** Standard FastAPI project structure. Dependency injection via FastAPI `Depends()`. Async throughout (asyncio subprocess, aiosqlite).
- **Conventions:** Python 3.12+, type hints everywhere, `uv` for package management, `pytest` for testing.
- **Key files:** PRD Section 5.1-5.5 defines all component specs. Section 5.5.1 has the complete REST API table.
- **Gotchas:**
  - Chromium `--kiosk` mode ignores window geometry — must use `--app` mode (PRD Section 5.1.1)
  - `pactl` sink-inputs may not appear immediately after Chromium launch — need polling (PRD Section 5.4.2)
  - python-xlib window operations need the X11 DISPLAY environment variable
  - Layout geometry computation must handle gap_px correctly to avoid 1px gaps/overlaps (PRD Section 5.2.2)
- **Domain context:** A "cell" is a Chromium window showing one streaming source. A "layout" defines how cells are arranged on screen. The "active audio cell" is the only one whose audio goes to HDMI speakers.
- **Mock mode:** When `HOMEVIEW_MOCK=1` or `--mock` flag is set, all system calls (Chromium launch, X11 operations, pactl commands) are replaced with no-op stubs that simulate success. The engine state machine and API logic run identically.

## Runtime Environment

- **Start command:** `uv run python -m server.main` (or `homeview start`)
- **Port:** 8000 (configurable)
- **Health check:** `GET /api/v1/server/health`

## Assumptions

- Python 3.12+ is available on the target system — supported by dev environment check (Python 3.12.3)
- `uv` is the package manager — confirmed available at `/home/msmiles/.local/bin/uv`
- X11, Chromium, xdotool, wmctrl, pactl are available on the deployment target (not in dev WSL2) — mock mode handles their absence during development
- SQLite is sufficient for single-operator persistence — per PRD decision
- FastAPI + Uvicorn provides async REST + WebSocket in a single process — standard pattern
- Layout JSON files are shipped with the project, not user-editable (users create presets, not layouts)

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| python-xlib API differs across X11 implementations | Medium | High | Abstract behind a WindowManager interface; mock mode tests the interface contract |
| pactl output format varies between PulseAudio and PipeWire | Medium | Medium | Parse pactl output defensively; test with both formats in unit tests |
| Multiple Chromium sink-inputs per process | Medium | Medium | Route ALL sink-inputs matching the PID, not just the first |
| Async subprocess management complexity | Low | High | Use asyncio.create_subprocess_exec with proper cleanup on shutdown |
| Layout geometry rounding causes 1px gaps | Medium | Low | Validation function checks that cell pixel sizes sum to display dimensions |

## Goal Verification

### Truths

1. The server starts in mock mode without any system dependencies (X11, Chromium, pactl)
2. All REST API endpoints from PRD Section 5.5.1 return correct responses
3. Assigning a source to a cell triggers Chromium launch (or mock equivalent) with correct flags
4. Switching layouts preserves source assignments per PRD Section 5.2.3 rules
5. Audio routing changes the active cell's sink-input to HDMI and others to null sink
6. Pairing with correct 6-digit code returns a Bearer token; incorrect code returns 401
7. Presets save current state and restore it on apply
8. Cell crash triggers automatic restart with backoff
9. WebSocket emits state.updated events on state changes

### Artifacts

1. `server/main.py` — FastAPI application entry point
2. `server/composition/engine.py` — Core engine managing cell lifecycle
3. `server/composition/cell.py` — Cell class wrapping Chromium process
4. `server/composition/layout.py` — Layout loading and geometry computation
5. `server/composition/window.py` — X11 window management via python-xlib
6. `server/audio/router.py` — PulseAudio routing
7. `server/api/routes.py` — REST endpoint definitions
8. `server/api/websocket.py` — WebSocket handler
9. `tests/` — Comprehensive test suite

## Progress Tracking

- [x] Task 1: Project scaffolding and configuration
- [x] Task 2: Database layer and models
- [x] Task 3: Source registry
- [x] Task 4: Layout system
- [x] Task 5: Window manager (python-xlib)
- [x] Task 6: Cell manager and Chromium process lifecycle
- [x] Task 7: Composition engine
- [x] Task 8: Audio router
- [x] Task 9: Health monitor
- [x] Task 10: Pairing and authentication (incl. `homeview reset-pairing` CLI + `GET /api/v1/pair/code`)
- [x] Task 11: FastAPI REST endpoints
- [x] Task 12: WebSocket and state broadcasting
- [x] Task 13: Preset system
- [x] Task 14: Interactive mode
- [x] Task 15: Integration tests and mock mode validation

**Total Tasks:** 15 | **Completed:** 15 | **Remaining:** 0

## Implementation Tasks

### Task 1: Project Scaffolding and Configuration

**Objective:** Set up the Python project structure, dependencies, configuration system, and mock mode support.
**Dependencies:** None

**Files:**

- Create: `pyproject.toml`
- Create: `server/__init__.py`
- Create: `server/main.py` (minimal — just enough to run)
- Create: `server/config.py`
- Create: `server/composition/__init__.py`
- Create: `server/audio/__init__.py`
- Create: `server/sources/__init__.py`
- Create: `server/api/__init__.py`
- Create: `server/auth/__init__.py`
- Create: `server/presets/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Test: `tests/test_config.py`

**Key Decisions / Notes:**

- Use `uv` for package management with `pyproject.toml`
- Dependencies: `fastapi`, `uvicorn[standard]`, `aiosqlite`, `python-xlib`, `pydantic`, `pydantic-settings`
- Dev dependencies: `pytest`, `pytest-asyncio`, `httpx` (for FastAPI test client)
- Config via `pydantic-settings`: reads from env vars and `.env` file
- `HOMEVIEW_MOCK=1` env var activates mock mode — stored in config as `mock_mode: bool`
- Config includes: `host`, `port`, `db_path`, `profiles_dir`, `layouts_dir`, `mock_mode`, `display` (DISPLAY env)
- `server/main.py` creates a minimal FastAPI app that starts with `uv run python -m server.main`

**Definition of Done:**

- [ ] `uv run python -m server.main` starts the server on port 8000
- [ ] `GET /api/v1/server/health` returns `{"status": "ok"}`
- [ ] Config loads from env vars (HOMEVIEW_MOCK, HOMEVIEW_PORT, etc.)
- [ ] All tests pass: `uv run pytest tests/test_config.py -q`
- [ ] No diagnostics errors

**Verify:**

- `uv run pytest tests/test_config.py -q`
- `HOMEVIEW_MOCK=1 uv run python -m server.main &` then `curl http://localhost:8000/api/v1/server/health`

---

### Task 2: Database Layer and Models

**Objective:** Create SQLite database management with schema creation, and Pydantic models for all domain objects.
**Dependencies:** Task 1

**Files:**

- Create: `server/db.py`
- Create: `server/models.py`
- Test: `tests/test_db.py`
- Test: `tests/test_models.py`

**Key Decisions / Notes:**

- Use `aiosqlite` for async SQLite access
- Database path from config (default: `~/.homeview/homeview.db` or `./data/homeview.db`)
- Schema tables: `sources`, `presets`, `auth_tokens`, `server_state`
- `sources` table per PRD Section 5.3: id, name, type, url, icon_url, requires_widevine, notes, created_at, updated_at
- `presets` table: id, name, layout_id, cell_assignments (JSON), active_audio_cell, created_at
- `auth_tokens` table: id, token (hashed), created_at, is_active
- `server_state` table: key-value store for persistent state (current layout, pairing code, etc.)
- Auto-create schema on first run (CREATE TABLE IF NOT EXISTS)
- Seed default sources on first run (ESPN, Prime, Netflix per PRD Section 5.3)
- Pydantic models: `Source`, `SourceCreate`, `SourceUpdate`, `Layout`, `Cell`, `CellState`, `Preset`, `PresetCreate`, `AudioState`, `ServerStatus`, `PairingRequest`, `PairingResponse`, `ErrorResponse`
- Use Pydantic v2 model_validator for validation

**Definition of Done:**

- [ ] Database initializes with schema on first run
- [ ] Default sources (ESPN, Prime, Netflix) are seeded
- [ ] All Pydantic models validate correct data and reject invalid data
- [ ] Database can be created at configurable path
- [ ] All tests pass: `uv run pytest tests/test_db.py tests/test_models.py -q`

**Verify:**

- `uv run pytest tests/test_db.py tests/test_models.py -q`

---

### Task 3: Source Registry

**Objective:** Implement CRUD operations for the source registry backed by SQLite.
**Dependencies:** Task 2

**Files:**

- Create: `server/sources/registry.py`
- Test: `tests/test_sources.py`

**Key Decisions / Notes:**

- Async methods: `list_sources()`, `get_source(id)`, `create_source(data)`, `update_source(id, data)`, `delete_source(id)`
- Pre-loaded sources (ESPN, Prime, Netflix) are inserted on DB init — they can be updated but not deleted (type: `streaming`)
- Custom sources (type: `url`) can be fully CRUD'd
- Source ID is auto-generated (slug from name) for custom sources; pre-loaded have fixed IDs
- Return Pydantic `Source` models from all methods
- Raise appropriate exceptions: `SourceNotFoundError`, `SourceAlreadyExistsError`

**Definition of Done:**

- [ ] List all sources returns pre-loaded + custom
- [ ] Create custom source with name + URL succeeds
- [ ] Update source updates fields, sets updated_at
- [ ] Delete custom source succeeds; delete pre-loaded raises error
- [ ] Get non-existent source raises SourceNotFoundError
- [ ] All tests pass: `uv run pytest tests/test_sources.py -q`

**Verify:**

- `uv run pytest tests/test_sources.py -q`

---

### Task 4: Layout System

**Objective:** Implement layout loading from JSON files, geometry computation, and deterministic layout switching logic.
**Dependencies:** Task 1

**Files:**

- Create: `server/composition/layout.py`
- Create: `layouts/single.json`
- Create: `layouts/side_by_side.json`
- Create: `layouts/2x2.json`
- Create: `layouts/hero_3side.json`
- Create: `layouts/pip.json`
- Test: `tests/test_layout.py`

**Key Decisions / Notes:**

- Layout JSON format per PRD Section 5.2: `{ "name", "id", "gap_px", "cells": [{ "id", "role", "x", "y", "w", "h" }] }`
- `LayoutManager` class: `load_layouts(dir)`, `get_layout(id)`, `list_layouts()`, `compute_geometry(layout, display_width, display_height) -> list[CellGeometry]`
- `CellGeometry`: dataclass with `cell_id, x, y, width, height` (pixel values)
- Geometry computation per PRD Section 5.2.2 — handle gap_px correctly
- Validation: cell proportions sum to 1.0 per axis, no overlaps
- `compute_transition(old_layout, new_layout, old_assignments) -> new_assignments` per PRD Section 5.2.3:
  - hero->hero first, then side->side by position order, then remaining by id alphabetical
  - Fewer cells: drop grid->side->pip priority, remember dropped
  - More cells: new cells empty
  - Audio: if active audio dropped, move to hero or first available
- All 5 layout JSON files per PRD Section 5.2.1

**Definition of Done:**

- [ ] All 5 layout JSON files load and validate correctly
- [ ] Geometry computation produces correct pixel positions for 1920x1080 and 3840x2160
- [ ] gap_px is applied correctly (no 1px gaps or overlaps)
- [ ] Layout transition preserves sources per PRD rules
- [ ] Transition handles fewer cells, more cells, and audio cell migration
- [ ] All tests pass: `uv run pytest tests/test_layout.py -q`

**Verify:**

- `uv run pytest tests/test_layout.py -q`

---

### Task 5: Window Manager (python-xlib)

**Objective:** Implement X11 window management: find windows by PID, set geometry, remove decorations, enforce placement.
**Dependencies:** Task 1

**Files:**

- Create: `server/composition/window.py`
- Test: `tests/test_window.py`

**Key Decisions / Notes:**

- `WindowManager` class with abstract interface + two implementations:
  - `X11WindowManager` — real python-xlib implementation
  - `MockWindowManager` — returns success for all operations, tracks state in-memory
- Factory function: `create_window_manager(mock_mode: bool) -> WindowManager`
- Interface methods:
  - `find_window_by_pid(pid, timeout=10.0) -> Optional[int]` (window ID)
  - `set_geometry(window_id, x, y, width, height)`
  - `remove_decorations(window_id)`
  - `set_always_on_top(window_id)`
  - `get_geometry(window_id) -> tuple[x, y, w, h]`
  - `close_window(window_id)`
- `X11WindowManager` uses python-xlib's `Display`, `Window` objects
  - `find_window_by_pid`: walk window tree checking `_NET_WM_PID` property, poll with 100ms interval. If `_NET_WM_PID` is not set (observed on some X11 setups), fall back to matching by `WM_CLASS` containing "chromium" and correlating with `--user-data-dir` suffix in the window title or command line
  - `remove_decorations`: set `_MOTIF_WM_HINTS` to remove all decorations
  - `set_geometry`: use `configure_window` and `move_resize_window`
- Mock implementation logs all calls and simulates window IDs (incrementing counter)

**Definition of Done:**

- [ ] MockWindowManager passes all interface tests
- [ ] X11WindowManager methods are implemented (tested via mock in CI, real X11 on deployment)
- [ ] find_window_by_pid polls correctly with timeout
- [ ] remove_decorations sets _MOTIF_WM_HINTS
- [ ] set_geometry applies position and size correctly
- [ ] All tests pass: `uv run pytest tests/test_window.py -q`

**Verify:**

- `uv run pytest tests/test_window.py -q`

---

### Task 6: Cell Manager and Chromium Process Lifecycle

**Objective:** Implement the Cell class that wraps a Chromium subprocess with correct launch flags, profile isolation, and lifecycle management.
**Dependencies:** Task 1, Task 5

**Files:**

- Create: `server/composition/cell.py`
- Test: `tests/test_cell.py`

**Key Decisions / Notes:**

- `Cell` class manages one Chromium process:
  - `cell_id: str`, `source_id: Optional[str]`, `url: Optional[str]`, `process: Optional[asyncio.subprocess.Process]`, `window_id: Optional[int]`, `status: CellStatus` (enum: EMPTY, STARTING, RUNNING, RESTARTING, FAILED)
  - `async launch(url, source_id)` — start Chromium with `--app` mode and all PRD flags (Section 5.1.1)
  - `async stop()` — terminate Chromium process, clean up
  - `async restart()` — stop then launch with same URL
  - `pid` property — returns process PID
- Chromium launch flags per PRD Section 5.1.1 (use `--app`, NOT `--kiosk`)
- Profile directory: `{config.profiles_dir}/cell-{cell_id}/`
- `ChromiumLauncher` abstraction:
  - `RealChromiumLauncher` — uses `asyncio.create_subprocess_exec`
  - `MockChromiumLauncher` — returns a mock process object with controllable behavior
- Factory: `create_chromium_launcher(mock_mode: bool) -> ChromiumLauncher`
- Cell tracks its own state transitions: EMPTY -> STARTING -> RUNNING, and RUNNING -> RESTARTING -> RUNNING or FAILED

**Definition of Done:**

- [ ] Cell launches Chromium with correct `--app` flags (not `--kiosk`)
- [ ] Cell uses isolated `--user-data-dir` per cell_id
- [ ] Cell.stop() terminates the process cleanly
- [ ] Cell tracks status transitions correctly
- [ ] MockChromiumLauncher works for testing without real Chromium
- [ ] All tests pass: `uv run pytest tests/test_cell.py -q`

**Verify:**

- `uv run pytest tests/test_cell.py -q`

---

### Task 7: Composition Engine

**Objective:** Implement the core engine that orchestrates cells, layouts, window placement, and state management.
**Dependencies:** Task 4, Task 5, Task 6

**Files:**

- Create: `server/composition/engine.py`
- Test: `tests/test_engine.py`

**Key Decisions / Notes:**

- `CompositionEngine` class — the central coordinator:
  - Holds current layout, cell states, source assignments, active audio cell
  - `async start()` — detect display, load default layout (single), initialize cells
  - `async stop()` — stop all cells, clean up
  - `async set_layout(layout_id)` — switch layout with deterministic transition (Task 4)
  - `async assign_source(cell_id, source_id)` — launch/change source in a cell
  - `async clear_cell(cell_id)` — stop cell, mark empty
  - `async set_active_audio(cell_id)` — delegate to audio router
  - `get_state() -> EngineState` — full snapshot for API/WebSocket
- After launching a cell's Chromium process:
  1. Wait for window via WindowManager.find_window_by_pid()
  2. Apply geometry from current layout via WindowManager.set_geometry()
  3. Remove decorations, set always-on-top
  4. Mark cell as RUNNING
- Periodic geometry enforcement: background task checks every 5 seconds
- Display detection: parse `xrandr` output for primary display resolution (or mock)
- State change callback: engine emits events that the WebSocket handler subscribes to
- Engine holds references to: LayoutManager, WindowManager, AudioRouter, SourceRegistry

**Definition of Done:**

- [ ] Engine starts with default `single` layout
- [ ] set_layout() switches layout and preserves source assignments
- [ ] assign_source() launches Chromium and enforces window geometry
- [ ] clear_cell() stops Chromium and marks cell empty
- [ ] get_state() returns complete snapshot matching PRD status format
- [ ] State changes trigger callback notifications
- [ ] Geometry enforcement runs periodically (5s interval)
- [ ] Display resolution change triggers geometry recompute and re-enforcement for all running cells without restart
- [ ] All tests pass: `uv run pytest tests/test_engine.py -q`

**Verify:**

- `uv run pytest tests/test_engine.py -q`

---

### Task 8: Audio Router

**Objective:** Implement PulseAudio-compatible audio routing: active cell to HDMI, all others to null sink.
**Dependencies:** Task 1

**Files:**

- Create: `server/audio/router.py`
- Test: `tests/test_audio.py`

**Key Decisions / Notes:**

- `AudioRouter` abstract interface + two implementations:
  - `PulseAudioRouter` — real pactl commands via asyncio subprocess
  - `MockAudioRouter` — tracks routing state in-memory
- Factory: `create_audio_router(mock_mode: bool) -> AudioRouter`
- Interface methods:
  - `async setup()` — create null sink (`pactl load-module module-null-sink sink_name=homeview_mute`), find HDMI sink
  - `async route_to_hdmi(pid: int)` — find sink-inputs for PID, move to HDMI sink
  - `async route_to_mute(pid: int)` — find sink-inputs for PID, move to null sink
  - `async set_active_cell(active_pid: int, all_pids: list[int])` — route active to HDMI, all others to mute
  - `async cleanup()` — unload null sink module
  - `get_hdmi_sink() -> Optional[str]` — cached HDMI sink name
- PulseAudioRouter implementation:
  - Parse `pactl list sinks short` to find HDMI sink
  - Parse `pactl list sink-inputs` to find sink-inputs by PID (match `application.process.id`)
  - Handle multiple sink-inputs per PID (route all)
  - Poll for sink-inputs after cell launch (500ms interval, 30s timeout per PRD)
  - `pactl subscribe` subprocess started in `PulseAudioRouter.setup()` as an asyncio background task; cancelled via `task.cancel()` in `cleanup()` — must not hang on shutdown
  - Subscribe event parsing: lines of the form `Event 'new' on sink-input #N` trigger a re-check of routing for the new sink-input; parse errors are logged and skipped (not fatal), as PulseAudio and PipeWire emit slightly different formats
- MockAudioRouter: dictionary of pid -> sink_name, validates all operations; exposes `inject_sink_input_event(pid)` method for tests to simulate new sink-input arrivals without a real pactl process

**Definition of Done:**

- [ ] setup() creates null sink and finds HDMI sink
- [ ] route_to_hdmi() moves sink-inputs for a PID to HDMI
- [ ] route_to_mute() moves sink-inputs for a PID to null sink
- [ ] set_active_cell() routes active to HDMI and all others to mute in one call
- [ ] Handles multiple sink-inputs per PID
- [ ] MockAudioRouter tracks routing state correctly and inject_sink_input_event() works in tests
- [ ] PulseAudioRouter.cleanup() cancels the subscribe background task without hanging
- [ ] All tests pass: `uv run pytest tests/test_audio.py -q`

**Verify:**

- `uv run pytest tests/test_audio.py -q`

---

### Task 9: Health Monitor

**Objective:** Implement crash detection, exponential backoff restart, and crash-loop protection for cells.
**Dependencies:** Task 6, Task 7

**Files:**

- Create: `server/composition/health.py`
- Test: `tests/test_health.py`

**Key Decisions / Notes:**

- `HealthMonitor` class — watches cell processes and manages restarts:
  - Monitors each cell's process for exit (via asyncio process wait or polling)
  - On crash (non-zero exit): trigger restart with backoff
  - Exponential backoff per PRD Section 5.1.3: 1s, 2s, 4s, 8s, 16s, max 60s
  - Reset backoff after 5 minutes of stable operation
  - Crash limit: 5 consecutive crashes in 5 minutes -> mark cell FAILED, stop restarting
  - On restart: re-launch same source URL, re-enforce geometry, re-route audio if active
- `CellHealthState`: dataclass tracking crash_count, last_crash_time, backoff_seconds, consecutive_crashes
- Integrates with CompositionEngine: engine registers cells, health monitor watches them
- Emits health events: `cell_restarting`, `cell_recovered`, `cell_failed`
- Background asyncio task per monitored cell

**Definition of Done:**

- [ ] Detects cell process exit within 1 second
- [ ] Restarts with exponential backoff (1s, 2s, 4s, 8s, 16s, max 60s)
- [ ] Backoff resets after 5 minutes of stable operation
- [ ] After 5 consecutive crashes in 5 minutes, marks cell FAILED
- [ ] Emits correct health events for each state transition
- [ ] All tests pass: `uv run pytest tests/test_health.py -q`

**Verify:**

- `uv run pytest tests/test_health.py -q`

---

### Task 10: Pairing and Authentication

**Objective:** Implement pairing flow (6-digit code), Bearer token generation, and auth middleware.
**Dependencies:** Task 2

**Files:**

- Create: `server/auth/tokens.py`
- Create: `server/auth/pairing.py`
- Create: `server/auth/middleware.py`
- Create: `server/cli.py` (homeview reset-pairing entry point)
- Test: `tests/test_auth.py`

**Key Decisions / Notes:**

- `PairingManager`:
  - `generate_pairing_code() -> str` — random 6-digit code, stored in DB with expiry (5 minutes)
  - `validate_code(code) -> Optional[str]` — returns Bearer token on success, None on failure
  - `get_current_code() -> Optional[dict]` — returns `{code, expires_at}` if in pairing mode, None if already paired
  - `is_paired() -> bool` — check if any active token exists
  - `reset_pairing()` — delete all tokens, generate new pairing code
- `TokenManager`:
  - `create_token() -> str` — generate secure random token (secrets.token_urlsafe)
  - `validate_token(token) -> bool` — check against DB (hash comparison)
  - Token stored as SHA-256 hash in DB
- `AuthMiddleware` (FastAPI dependency):
  - Extract `Authorization: Bearer <token>` header
  - Validate against TokenManager
  - Return 401 if invalid/missing
  - Skip auth for `POST /api/v1/pair` and `GET /api/v1/pair/code` endpoints
- On first boot: no active tokens -> pairing mode (generate code)
- After successful pairing: code is consumed, token is active
- `homeview reset-pairing` CLI: `console_scripts` entry in pyproject.toml pointing to `server.cli:reset_pairing`. Calls `PairingManager.reset_pairing()` synchronously and prints confirmation. Does not require the server to be running.

**Definition of Done:**

- [ ] Pairing code is 6 digits, expires after 5 minutes
- [ ] `GET /api/v1/pair/code` returns `{code, expires_at}` in pairing mode; 404 if already paired
- [ ] Correct code returns a Bearer token
- [ ] Incorrect code returns 401
- [ ] Bearer token authenticates subsequent requests
- [ ] Token is stored as SHA-256 hash (not plaintext)
- [ ] Auth middleware rejects requests without valid token (except pairing endpoints)
- [ ] reset_pairing() clears tokens and generates new code
- [ ] `homeview reset-pairing` CLI command clears all tokens and generates a new pairing code
- [ ] All tests pass: `uv run pytest tests/test_auth.py -q`

**Verify:**

- `uv run pytest tests/test_auth.py -q`

---

### Task 11: FastAPI REST Endpoints

**Objective:** Implement all REST API endpoints per PRD Section 5.5.1, wiring them to the engine and registries.
**Dependencies:** Task 3, Task 7, Task 8, Task 10

**Files:**

- Create: `server/api/routes.py`
- Create: `server/api/dependencies.py`
- Modify: `server/main.py` (wire up routes, engine startup/shutdown)
- Test: `tests/test_api.py`

**Key Decisions / Notes:**

- All endpoints per PRD Section 5.5.1:
  - `POST /api/v1/pair` — pairing (no auth)
  - `GET /api/v1/pair/code` — retrieve current pairing code (no auth; returns `{code, expires_at}` or 404)
  - `GET /api/v1/status` — full state snapshot
  - `GET /api/v1/layouts` — list layouts
  - `PUT /api/v1/layout` — apply layout
  - `GET /api/v1/sources` — list sources
  - `POST /api/v1/sources` — add source
  - `PUT /api/v1/sources/{id}` — update source
  - `DELETE /api/v1/sources/{id}` — delete source
  - `PUT /api/v1/cells/{cell_id}/source` — assign source to cell
  - `DELETE /api/v1/cells/{cell_id}/source` — clear cell
  - `PUT /api/v1/audio/active` — set active audio cell
  - `GET /api/v1/presets` — list presets (stub, implemented in Task 13)
  - `POST /api/v1/presets` — save preset (stub)
  - `PUT /api/v1/presets/{id}/apply` — apply preset (stub)
  - `DELETE /api/v1/presets/{id}` — delete preset (stub)
  - `POST /api/v1/interactive/start` — start interactive mode (stub, Task 14)
  - `POST /api/v1/interactive/stop` — stop interactive mode (stub)
  - `GET /api/v1/server/info` — server info
  - `GET /api/v1/server/health` — health check
- `server/api/dependencies.py`: FastAPI dependency injection for engine, source registry, auth
- Error responses per PRD Section 5.5.3: `{ "error": { "code", "message", "details" } }`
- Preset and interactive mode endpoints are stubs returning HTTP 501 with `{ "error": { "code": "NOT_IMPLEMENTED", "message": "...", "details": {} } }` until Tasks 13/14
- `server/main.py` lifespan: start engine on startup, stop on shutdown
- Auth middleware applied to all routes except `POST /api/v1/pair`, `GET /api/v1/pair/code`, and `GET /api/v1/server/health`

**Definition of Done:**

- [ ] All endpoints from PRD Section 5.5.1 are implemented (presets/interactive as stubs)
- [ ] Preset and interactive mode stub endpoints return HTTP 501 with error body matching PRD Section 5.5.3 format
- [ ] Auth middleware blocks unauthenticated requests (except pair, pair/code, health)
- [ ] `GET /api/v1/status` returns complete state snapshot
- [ ] `PUT /api/v1/layout` triggers layout switch in engine
- [ ] `PUT /api/v1/cells/{cell_id}/source` assigns source and launches cell
- [ ] `PUT /api/v1/audio/active` changes active audio cell
- [ ] Error responses match PRD format
- [ ] All tests pass: `uv run pytest tests/test_api.py -q`

**Verify:**

- `uv run pytest tests/test_api.py -q`

---

### Task 12: WebSocket and State Broadcasting

**Objective:** Implement WebSocket endpoint for real-time state updates and cell health events.
**Dependencies:** Task 7, Task 11

**Files:**

- Create: `server/api/websocket.py`
- Create: `server/api/events.py`
- Modify: `server/main.py` (register WebSocket route)
- Modify: `server/composition/engine.py` (connect event emitter)
- Test: `tests/test_websocket.py`

**Key Decisions / Notes:**

- WebSocket endpoint: `GET /ws/control`
- Auth: Bearer token as query param (`?token=...`) or first message `{ "type": "auth", "token": "..." }`
- `ConnectionManager` class:
  - `connect(websocket, token)` — validate token, add to active connections
  - `disconnect(websocket)` — remove from active connections
  - `broadcast(event)` — send to all connected clients
- Events per PRD Section 5.5.2:
  - `state.updated` — full state snapshot on any state change
  - `cell.health` — `{ cell_id, status, message }` on crash/recovery
  - `pairing.complete` — `{ server_name }` on successful pairing
- `EventBus` class: engine and other components publish events, WebSocket handler subscribes
  - Uses asyncio.Queue per connection for backpressure
- Engine calls `event_bus.emit("state.updated", state)` on every state change
- Health monitor calls `event_bus.emit("cell.health", {cell_id, status, message})`

**Definition of Done:**

- [ ] WebSocket connection requires valid token
- [ ] state.updated event fires on layout change, source assignment, audio change
- [ ] cell.health event fires on cell crash, restart, recovery, failure
- [ ] Multiple clients receive all broadcasts
- [ ] Disconnected clients are cleaned up
- [ ] All tests pass: `uv run pytest tests/test_websocket.py -q`

**Verify:**

- `uv run pytest tests/test_websocket.py -q`

---

### Task 13: Preset System

**Objective:** Implement preset save/load/apply backed by SQLite.
**Dependencies:** Task 2, Task 7, Task 11

**Files:**

- Create: `server/presets/manager.py`
- Modify: `server/api/routes.py` (replace preset stubs with real implementations)
- Test: `tests/test_presets.py`

**Key Decisions / Notes:**

- `PresetManager` class:
  - `async save_preset(name) -> Preset` — capture current engine state (layout_id, cell_assignments, active_audio_cell)
  - `async apply_preset(preset_id)` — restore state via engine (set_layout, assign sources, set audio)
  - `async list_presets() -> list[Preset]`
  - `async delete_preset(preset_id)`
- Preset schema per PRD Section 8.1: id (slug from name), name, layout_id, cell_assignments (JSON dict), active_audio_cell, created_at
- Application per PRD Section 8.2:
  1. Switch to preset's layout
  2. Assign sources per cell_assignments (null = clear)
  3. Set active audio cell
  4. If a source in the preset was deleted, skip and log warning
- Wire into existing API route stubs from Task 11

**Definition of Done:**

- [ ] Save current state as named preset
- [ ] List all presets
- [ ] Apply preset restores layout, sources, and audio
- [ ] Apply handles deleted sources gracefully (skip + warning)
- [ ] Delete preset removes from DB
- [ ] API endpoints return correct responses
- [ ] All tests pass: `uv run pytest tests/test_presets.py -q`

**Verify:**

- `uv run pytest tests/test_presets.py -q`

---

### Task 14: Interactive Mode

**Objective:** Implement interactive mode start/stop per cell — relaxes window enforcement for manual interaction.
**Dependencies:** Task 7, Task 11

**Files:**

- Create: `server/composition/interactive.py`
- Modify: `server/api/routes.py` (replace interactive stubs)
- Modify: `server/composition/engine.py` (integrate interactive mode)
- Test: `tests/test_interactive.py`

**Key Decisions / Notes:**

- `InteractiveManager` class:
  - `start(cell_id)` — pause geometry enforcement for that cell, allow focus, mark as interactive
  - `stop()` — re-enforce geometry on all cells, clear interactive state
  - `is_active() -> bool`
  - `active_cell_id -> Optional[str]`
- Only one cell can be interactive at a time (per PRD — POST interactive/stop has no body)
- When interactive:
  - Geometry enforcement loop skips the interactive cell
  - Window is NOT set to always-on-top (allow interaction)
  - Cell status changes to INTERACTIVE
- When stopped: re-apply geometry + decorations + always-on-top
- API: 409 if interactive mode already active for a different cell

**Definition of Done:**

- [ ] Start interactive mode pauses geometry enforcement for the cell
- [ ] Only one cell can be interactive at a time
- [ ] Stop re-enforces geometry on all cells
- [ ] 409 error if interactive already active on different cell
- [ ] Engine state reflects interactive status
- [ ] API endpoints return correct responses
- [ ] All tests pass: `uv run pytest tests/test_interactive.py -q`

**Verify:**

- `uv run pytest tests/test_interactive.py -q`

---

### Task 15: Integration Tests and Mock Mode Validation

**Objective:** End-to-end integration tests exercising the full API in mock mode, validating all PRD user flows.
**Dependencies:** Task 11, Task 12, Task 13, Task 14

**Files:**

- Create: `tests/test_integration.py`
- Create: `scripts/homeview.service`

**Key Decisions / Notes:**

- Integration tests use FastAPI's TestClient with `HOMEVIEW_MOCK=1`
- Test scenarios mapping to PRD Section 7 (Core User Flows):
  - **Flow 1 (Setup):** Pair -> verify auth -> get status (empty single layout)
  - **Flow 2 (Multi-Stream):** Set layout 2x2 -> assign ESPN/Netflix/Prime to 3 cells -> set audio -> verify status
  - **Flow 3 (Preset):** Save current state as preset -> switch to different layout -> apply preset -> verify restoration
  - **Flow 4 (Crash Recovery):** Assign source -> simulate crash (mock) -> verify restart and state recovery
  - **WebSocket flow:** Connect WS -> perform actions -> verify events received
  - **Layout transition:** 2x2 -> hero_3side -> verify source preservation per PRD rules
  - **Audio routing:** Switch active audio between cells -> verify routing state
  - **Interactive mode:** Start interactive -> verify geometry paused -> stop -> verify re-enforced
  - **Display resolution change:** Assign sources -> simulate xrandr resolution change (mock: update mock return value) -> verify engine recomputes geometry and re-enforces all cell windows
  - **Pairing flow (GET code):** Server in pairing mode -> `GET /api/v1/pair/code` returns 6-digit code -> pair with code -> `GET /api/v1/pair/code` returns 404
  - **Error cases:** Invalid token -> 401, invalid cell_id -> 404, invalid layout_id -> 404, stub endpoints -> 501
- systemd service file: `scripts/homeview.service` per PRD Section 11

**Definition of Done:**

- [ ] All integration test scenarios pass in mock mode
- [ ] Full API flow: pair -> configure -> preset -> crash recovery
- [ ] WebSocket receives events for all state changes
- [ ] Error responses match PRD format for all error cases
- [ ] systemd service file is valid
- [ ] All tests pass: `uv run pytest tests/ -q`
- [ ] Zero test failures across entire suite

**Verify:**

- `uv run pytest tests/ -q`

---

## Open Questions

1. **Chromium binary name**: The binary might be `chromium-browser`, `chromium`, or `google-chrome` depending on distro. Config should support specifying the binary path.
2. **Profile directory location**: PRD says `/var/lib/homeview/profiles/` but that requires root. Consider `~/.homeview/profiles/` as default.
3. **Display detection in mock mode**: Should mock mode simulate a specific resolution (e.g., 1920x1080) or be configurable?

### Deferred Ideas

- CLI tool (`homeview start`, `homeview reset-pairing`, `homeview status`) — can be added as a thin wrapper around the API
- Pairing overlay display on TV — requires a separate display process (Chromium page or Python GUI)
- HTTPS/TLS certificate auto-generation — document as a manual setup step for now
