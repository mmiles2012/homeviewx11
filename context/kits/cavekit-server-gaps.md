---
created: "2026-04-19T00:00:00Z"
last_edited: "2026-04-19T00:00:00Z"
complexity: medium
---

# Cavekit: Server Gaps

## Scope

Four deferred server-side fixes from the v1-server spec. All changes are confined to the `server/` Python package. No new REST endpoints are introduced; this kit corrects existing behavior and adds supporting infrastructure for the PWA.

## Requirements

### R1: Pairing Error Envelope

**Description:** The pairing routes (`GET /api/v1/pair/code` and `POST /api/v1/pair`) must return errors in the project-standard error envelope format instead of bare `HTTPException` detail strings.

**Acceptance Criteria:**
- [ ] `GET /api/v1/pair/code` returns HTTP 404 with body `{"error": {"code": "NOT_PAIRED_OR_EXPIRED", "message": "<string>", "details": {}}}` when no active pairing code exists
- [ ] `POST /api/v1/pair` returns HTTP 401 with body `{"error": {"code": "INVALID_PAIRING_CODE", "message": "<string>", "details": {}}}` when the submitted code is wrong or expired
- [ ] `POST /api/v1/pair` returns HTTP 409 with body `{"error": {"code": "ALREADY_PAIRED", "message": "<string>", "details": {}}}` when the server already has an active token
- [ ] All three error responses have a top-level `error` key containing exactly the keys `code`, `message`, and `details`
- [ ] `details` is always an object (never `null` or absent)
- [ ] Successful pairing responses are unchanged

**Dependencies:** None

### R2: Cell Health WebSocket Events

**Description:** The `HealthMonitor` must emit health events to connected WebSocket clients. Currently the monitor is constructed without an `on_event` callback, so health events are silently dropped.

**Acceptance Criteria:**
- [ ] When a cell transitions to `cell_restarting`, connected WebSocket clients receive a message with `{"type": "cell.health", "data": {"cell_index": <int>, "event_type": "cell_restarting", "detail": "<string>"}}`
- [ ] When a cell transitions to `cell_recovered`, connected WebSocket clients receive a message with `{"type": "cell.health", "data": {"cell_index": <int>, "event_type": "cell_recovered", "detail": "<string>"}}`
- [ ] When a cell transitions to `cell_failed`, connected WebSocket clients receive a message with `{"type": "cell.health", "data": {"cell_index": <int>, "event_type": "cell_failed", "detail": "<string>"}}`
- [ ] In mock mode, health events are emitted through the same path (no special-casing)

**Dependencies:** None

### R3: TV Pairing Overlay

**Description:** On first boot when the server is unpaired, a full-screen Chromium overlay must display the current pairing code. The overlay must close when pairing completes. The overlay must use the existing `Cell`/`ChromiumLauncher` abstraction so it remains testable under mock mode.

**Acceptance Criteria:**
- [ ] When the server starts unpaired (`PairingManager.is_paired()` returns `False`), a full-screen overlay launches displaying the pairing code
- [ ] The overlay uses the `Cell`/`ChromiumLauncher` abstraction (not raw subprocess calls)
- [ ] When pairing completes successfully, the overlay is closed (the Cell is stopped)
- [ ] The overlay is single-instance: only one overlay exists at a time regardless of lifecycle events
- [ ] In mock mode, `MockChromiumLauncher` handles the overlay (no real Chromium spawned)
- [ ] If the server starts already paired, no overlay is launched

**Dependencies:** R1 (pairing routes must be functional for the pairing flow to complete)

### R4: Static Serving and CORS

**Description:** The server must serve a static SPA from `server/static/` when present, and must enable CORS for cross-origin development access.

**Acceptance Criteria:**
- [ ] A `server/static/` directory exists in the repository with a `.gitkeep` file
- [ ] Contents of `server/static/` (except `.gitkeep`) are excluded from version control
- [ ] When `server/static/index.html` exists at runtime, the SPA is served at the root path `/`
- [ ] When `server/static/index.html` does not exist at runtime, the server starts without error and the root path `/` does not serve static files
- [ ] Direct navigation to SPA routes (e.g., `/pair`, `/settings`) returns the contents of `index.html` when it exists
- [ ] API routes under `/api/v1/` are never shadowed by the static file mount
- [ ] The WebSocket endpoint `/ws/control` is never shadowed by the static file mount
- [ ] CORS headers allow requests from origin `http://localhost:5173`
- [ ] In mock mode, CORS allows requests from any origin

**Dependencies:** None

## Out of Scope

- PWA application code (React, Vite, any frontend assets)
- New REST API endpoints beyond fixing existing pairing routes
- Audio routing changes
- Layout definition or source management changes
- Chromium launch flags or profile directory changes
- Changes to the `HealthMonitor` restart/backoff logic itself

## Cross-References

- See also: `cavekit-pwa-scaffold.md` (consumes the `server/static/` directory and CORS configuration from R4)
- See also: `cavekit-pwa-state.md` (consumes `cell.health` WebSocket events from R2)

## Changelog
