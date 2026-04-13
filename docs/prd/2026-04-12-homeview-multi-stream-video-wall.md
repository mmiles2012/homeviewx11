# HomeView — Multi-Stream Video Wall Controller

Created: 2026-04-12
Category: Feature
Status: Final
Research: Standard

## Problem Statement

No consumer-grade, self-hosted solution exists for turning a standard TV into a sports-bar-style multi-stream display. Commercial video wall software (Polywall, Userful, Datapath) targets enterprise control rooms at $1K+/display. OBS can composite sources but isn't designed for always-on, headless operation with phone-based remote control. Anthias (open-source digital signage) handles single-source display rotation, not simultaneous multi-stream composition.

HomeView fills this gap: a Linux server composites multiple streaming and web video sources into configurable layouts, outputting a single HDMI signal to a TV. A phone/tablet PWA controls everything. The TV is a dumb display — HDMI in, picture out.

---

## 1. Core Principles

- **Transparent to the TV.** The display is completely "dumb": HDMI in, picture out. No smart TV features needed.
- **Server as the brain.** All window composition, source management, and audio selection happen server-side.
- **Single operator (v1).** One household operator controls the system; no multi-user permissions in v1.
- **Sports-first latency.** Prefer low-latency and reliability over pixel-perfect composition when tradeoffs arise.
- **Manual intervention is acceptable.** Some streaming services require occasional manual interaction (login prompts, "still watching").
- **Fail gracefully.** Any single cell crash must not take down others. Recovery must be automatic and fast.

---

## 2. V1 Scope, Non-Goals, and Definitions

### 2.1 V1 Scope

1. A **Composition Engine** (Python) that launches and manages multiple Chromium "cells" positioned into a layout on X11.
2. A **Control Server** (FastAPI) exposing REST + WebSocket APIs.
3. A **Remote Control PWA** served by the server for configuration and control.
4. A **Source Registry** for known streaming/web sources.
5. **HDMI-only audio**: exactly one cell is the active audio source; all others muted.
6. **Pairing + auth**: secure LAN-based pairing with Bearer token authentication.
7. **Interactive Mode**: temporarily relax kiosk enforcement for manual login/interaction.

### 2.2 Non-Goals (v1)

| Non-Goal | Rationale |
|----------|-----------|
| Sonos / wireless audio | Deferred to v2 — requires Icecast pipeline and speaker discovery |
| Multi-TV orchestration | Deferred — one server instance = one TV in v1 |
| Multi-user accounts/roles | Single-operator simplicity; one paired remote |
| Automated login / "still watching" dismissal | Service-specific and brittle; Interactive Mode covers this manually |
| Perfect A/V sync across external audio | Out of scope without Sonos integration |
| CEC/IR input forwarding | Complex, low value for v1 |
| Wayland support | X11 only in v1; Wayland lacks mature multi-window placement tools |
| HDR / 4K DRM playback | Blocked by Widevine L3 limitation on Linux (see Technical Constraints) |

### 2.3 Supported Services (v1)

- **ESPN** (espn.com/watch)
- **Amazon Prime Video** (primevideo.com)
- **Netflix** (netflix.com)
- **Generic URL** (any web page)

**Definition of "supported":**
- HomeView launches the service URL in a Chromium cell with a persistent profile, maintains window placement, and restarts on crash.
- The user may need to log in or respond to prompts manually via Interactive Mode.
- **DRM resolution cap: 480p-720p** for Netflix/Prime on Linux. This is a Widevine L3 limitation — Google restricts Linux browsers to L3 (no TEE), capping resolution. Chrome OS gets L1 (1080p) via TPM/TEE attestation. No workaround exists. ESPN streams are generally not DRM-restricted and may achieve higher resolution.

### 2.4 Key Terms

| Term | Definition |
|------|-----------|
| **Server Instance** | One HomeView deployment controlling exactly one HDMI display output (v1) |
| **Cell** | One Chromium process/window controlled by HomeView, placed into a layout region |
| **Layout** | A template describing regions (cells) within a 1.0 x 1.0 coordinate space |
| **Source** | A named streaming/web target (URL + metadata) assignable to a cell |
| **Preset** | A saved configuration: layout + cell-to-source assignments + active-audio cell |
| **Active Audio Cell** | The single cell whose audio routes to HDMI; all others go to null sink |

---

## 3. System Architecture (v1)

```
+--------------------------------------------------+
|                  Linux Server                     |
|                                                   |
|  +---------------------------------------------+ |
|  |       Composition Engine (Python)            | |
|  |  - Launch/manage Chromium per cell           | |
|  |  - Compute geometry from layout              | |
|  |  - Enforce window placement (X11)            | |
|  |  - Watchdog / restart with backoff           | |
|  +---------------------------------------------+ |
|                                                   |
|  +---------------------------------------------+ |
|  |          Control Server (FastAPI)            | |
|  |  - REST + WebSocket APIs                     | |
|  |  - Pairing + Bearer token auth               | |
|  |  - Serves Remote PWA static assets           | |
|  +---------------------------------------------+ |
|                                                   |
|  +---------------------------------------------+ |
|  |    Audio Router (PulseAudio-compatible)      | |
|  |  - One active audio cell -> HDMI sink        | |
|  |  - All other cells -> null sink              | |
|  |  - PID-based sink-input identification       | |
|  +---------------------------------------------+ |
|                                                   |
+-------------------+-----------------------------+-+
                    |                             |
                    | LAN (HTTPS/WS)              | HDMI
                    v                             v
           +----------------+              +-----------+
           | Phone / Tablet |              |    TV     |
           | Remote PWA     |              +-----------+
           +----------------+
```

### 3.1 Atomic Unit: One Server Instance = One TV

- A HomeView server instance drives exactly one display output (one TV) in v1.
- Multi-TV households run multiple server instances (e.g., multiple small PCs or VMs).
- The Remote PWA can maintain a list of paired servers for future multi-server UX.

### 3.2 Technology Stack (v1)

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Composition Engine | Python 3.11+ | Rapid development, subprocess management, X11 library support |
| Web Server | FastAPI + Uvicorn | Async, WebSocket-native, serves PWA static files |
| Browser Engine | Chromium (--app mode) | Widest streaming compatibility, Widevine support |
| Window Management | X11 (xdotool/wmctrl or python-xlib) | Mature, scriptable; Wayland lacks equivalent tools |
| Audio Control | pactl (PulseAudio CLI) | Works on both PulseAudio and PipeWire (PA-compat layer) |
| Persistence | SQLite | Zero-config, single-file, sufficient for single-operator |
| Remote UI | PWA (HTML/CSS/JS) | No app store, works on any phone/tablet, installable |
| Process Manager | systemd | Standard Linux service management, auto-restart |

---

## 4. Pairing, Security, and Setup UX

### 4.1 Pairing Mode (First Run)

On first boot (or after reset), HomeView enters **Pairing Mode**:

1. The TV shows a minimal full-screen overlay:
   - Server name (default: hostname)
   - IP address / `.local` hostname (best effort via mDNS/Avahi)
   - A short-lived **6-digit pairing code** (expires after 5 minutes or on successful pair)
2. The user opens the PWA URL shown on screen from their phone.
3. The PWA prompts for the pairing code.
4. On success, the server issues a long-lived **Bearer token**.

### 4.2 Authentication Model

- All REST and WebSocket endpoints require `Authorization: Bearer <token>`.
- Token stored server-side in SQLite (single operator, v1).
- Remote stores token in browser localStorage.
- Token has no expiry in v1 (long-lived until manual reset).

### 4.3 Reset / Re-pair

- A local CLI command (`homeview reset-pairing`) or deleting the token from the database forces Pairing Mode on next start.
- Requires local/SSH access to the server — no remote reset in v1.

### 4.4 Network Security

- HomeView binds to LAN interfaces only (not 0.0.0.0 by default).
- HTTPS with self-signed cert (generated on first run) for PWA installability and secure WebSocket.
- The PWA must handle the self-signed cert trust prompt gracefully (documentation + instructions).

### 4.5 Interactive Mode

For manual login and prompt dismissal on streaming services:

- **Start**: API call designates a cell for interaction. The engine relaxes kiosk enforcement for that cell (allows focus, keyboard/mouse input routing).
- **Stop**: API call re-enforces kiosk constraints.
- V1 minimum: "pause kiosk enforcement" — the operator physically uses a keyboard/mouse connected to the server, or an attached remote/touchpad.
- Future: optional VNC/noVNC overlay accessible from the PWA (not v1).

---

## 5. Component Specifications

### 5.1 Composition Engine

The core Python process managing the lifecycle of all cells on the display.

**Responsibilities:**
- Launch/kill Chromium instances per cell with correct geometry and isolated profiles
- Apply layout templates by computing pixel positions from proportional definitions
- Handle layout transitions deterministically
- Monitor Chromium health (restart crashed instances with backoff)
- Expose state to the Control Server

#### 5.1.1 Cell Launching — Chromium Configuration

Each cell is a Chromium process launched via subprocess in **`--app` mode** (not `--kiosk`).

**Critical: `--kiosk` mode ignores `--window-size` and `--window-position`.** Research confirms this is a known Chromium behavior. Using `--app=<url>` preserves window geometry control while still providing a minimal chrome-less window.

**Required launch flags:**

```
chromium-browser \
  --app=https://www.espn.com/watch \
  --window-position=0,0 \
  --window-size=960,540 \
  --no-first-run \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --autoplay-policy=no-user-gesture-required \
  --disable-features=TranslateUI \
  --disable-background-timer-throttling \
  --disable-renderer-backgrounding \
  --user-data-dir=/var/lib/homeview/profiles/cell-<cell_id>
```

**Flag rationale:**

| Flag | Purpose |
|------|---------|
| `--app=<url>` | Chrome-less window with geometry control (NOT `--kiosk`) |
| `--window-position` / `--window-size` | Initial geometry hint (enforced post-launch by X11) |
| `--no-first-run` | Suppress first-run dialogs |
| `--disable-infobars` | Hide "controlled by automation" and similar bars |
| `--disable-session-crashed-bubble` | Suppress "restore pages" prompt after crash recovery |
| `--autoplay-policy=no-user-gesture-required` | Allow video autoplay without user interaction |
| `--disable-background-timer-throttling` | Prevent Chromium from throttling background tabs/windows |
| `--disable-renderer-backgrounding` | Keep renderer active even when window is not focused |
| `--user-data-dir` | Isolated profile per cell — logins, cookies, cache persist |

**Profile isolation strategy:** Each cell gets its own `--user-data-dir`. This ensures:
- Login sessions persist across restarts
- Cookie/cache isolation between cells
- One cell's crash doesn't corrupt another's profile

#### 5.1.2 Window Placement & Enforcement (X11)

The engine must reliably enforce window geometry after launch. Chromium creates windows asynchronously — initial flags are hints, not guarantees.

**Post-launch enforcement flow:**

1. Launch Chromium with `--app` and geometry flags.
2. Poll for the new window using PID matching (`xdotool search --pid <pid>`). Retry with 100ms intervals, timeout after 10 seconds.
3. Once window ID is found:
   - Remove decorations (`wmctrl -i -r <wid> -b add,fullscreen` or via `_MOTIF_WM_HINTS`)
   - Set position and size (`xdotool windowmove <wid> X Y && xdotool windowsize <wid> W H`)
   - Set always-on-top if needed (`wmctrl -i -r <wid> -b add,above`)
4. Store the window ID mapped to the cell ID.
5. **Periodic geometry enforcement**: re-check window geometry every 5 seconds. If a window has moved or resized (e.g., due to WM interference), re-apply. This handles edge cases like window manager resets or accidental interaction.

**Implementation choice (open):** Either `xdotool`/`wmctrl` via subprocess or `python-xlib` for direct X11 protocol. Both are viable; `python-xlib` avoids subprocess overhead for frequent geometry checks but adds a dependency.

**Window Manager requirement:** A minimal WM that doesn't fight window placement is recommended (e.g., Openbox with no auto-placement rules, or running without a WM on bare X11 with a simple root window).

#### 5.1.3 Health Monitoring & Restart

| Behavior | Specification |
|----------|--------------|
| Crash detection | Monitor Chromium process exit via `asyncio.subprocess` or SIGCHLD |
| Restart trigger | Any non-zero exit or process disappearance |
| Backoff | Exponential: 1s, 2s, 4s, 8s, 16s, max 60s. Reset after 5 minutes of stable operation. |
| State preservation | Restore last assigned source URL after restart |
| Crash limit | After 5 consecutive crashes within 5 minutes, mark cell as `FAILED` and notify PWA. Do not continue restarting. |
| Recovery action | On restart: launch with same source URL, re-enforce geometry, re-route audio if this was the active audio cell |

#### 5.1.4 Display Detection

On startup, the engine must:
1. Detect the primary display resolution (`xrandr` or `xdpyinfo`).
2. Compute pixel geometry for all cells based on the active layout and display resolution.
3. Recalculate if display resolution changes (monitor `xrandr --listen` events or poll).

---

### 5.2 Layout System

Layouts are defined as JSON files specifying proportional cell regions within a 1.0 x 1.0 coordinate space.

**Cell definition schema:**

```json
{
  "name": "1 Hero + 3 Sidebar",
  "id": "hero_3side",
  "gap_px": 2,
  "cells": [
    { "id": "main",  "role": "hero", "x": 0.0,  "y": 0.0,   "w": 0.75, "h": 1.0 },
    { "id": "side1", "role": "side", "x": 0.75, "y": 0.0,   "w": 0.25, "h": 0.333 },
    { "id": "side2", "role": "side", "x": 0.75, "y": 0.333, "w": 0.25, "h": 0.333 },
    { "id": "side3", "role": "side", "x": 0.75, "y": 0.666, "w": 0.25, "h": 0.334 }
  ]
}
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Stable layout identifier |
| `name` | string | Human-readable name for PWA display |
| `gap_px` | int | Pixel gap between cells (default: 2) |
| `cells[].id` | string | Stable cell identifier within the layout |
| `cells[].role` | enum | `hero`, `side`, `grid`, `pip` — used for transition mapping |
| `cells[].x/y/w/h` | float 0.0-1.0 | Proportional position and size |

#### 5.2.1 Included Layouts (v1)

| Layout | Cells | Description |
|--------|-------|-------------|
| `single` | 1 | Full-screen single source |
| `side_by_side` | 2 | Two equal halves, horizontal split |
| `2x2` | 4 | Four equal quadrants |
| `hero_3side` | 4 | 75% hero + 3 sidebar cells |
| `pip` | 2 | Full-screen main + small overlay (picture-in-picture) |

**3x3 (9 cells) is a stretch goal** — resource pressure with 9 Chromium instances is significant and window management complexity increases.

#### 5.2.2 Geometry Computation

Given display resolution `(W, H)` and a layout:

```
For each cell:
  pixel_x = round(cell.x * W) + gap_px
  pixel_y = round(cell.y * H) + gap_px
  pixel_w = round(cell.w * W) - (2 * gap_px)
  pixel_h = round(cell.h * H) - (2 * gap_px)
```

Ensure no sub-pixel rounding errors cause 1px gaps or overlaps. Validation: sum of all cell pixel widths per row must equal display width (minus gaps).

#### 5.2.3 Deterministic Layout Switching

When switching layouts, HomeView preserves source assignments:

1. Map `hero` -> `hero` (if present in both layouts).
2. Map `side` cells in stable order (top-to-bottom, left-to-right).
3. Map remaining cells in stable order by `id` alphabetical.
4. If new layout has **fewer** cells:
   - Drop lowest-priority roles first: `grid` -> `side` -> `pip`
   - Never drop `hero` unless new layout has no `hero`
   - Dropped sources are remembered (available for re-assignment)
5. If new layout has **more** cells:
   - New cells start empty (no source)
6. Audio: if the active audio cell is dropped, audio moves to the `hero` cell (or first available cell).

---

### 5.3 Source Registry

A persistent store of sources in SQLite.

**Schema:**

```sql
CREATE TABLE sources (
  id          TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  type        TEXT NOT NULL CHECK(type IN ('streaming', 'url')),
  url         TEXT NOT NULL,
  icon_url    TEXT,
  requires_widevine BOOLEAN DEFAULT FALSE,
  notes       TEXT,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Pre-loaded sources (v1):**

| ID | Name | Type | URL | Widevine | Notes |
|----|------|------|-----|----------|-------|
| `espn` | ESPN | streaming | https://www.espn.com/watch | No | Best streaming experience on Linux |
| `prime` | Amazon Prime Video | streaming | https://www.primevideo.com | Yes | Max 720p on Linux (Widevine L3) |
| `netflix` | Netflix | streaming | https://www.netflix.com | Yes | Max 480-720p on Linux (Widevine L3) |

#### 5.3.1 Source Types (v1)

- `streaming` — Known streaming services with specific configuration needs
- `url` — Generic web pages (sports scores, dashboards, cameras, etc.)

#### 5.3.2 Custom Sources

Users can add custom URL sources via the PWA. Custom sources require only a name and URL. The PWA provides a simple add/edit/delete CRUD interface.

---

### 5.4 Audio Router (v1: HDMI-Only)

Audio is intentionally simple in v1 to ensure reliability.

#### 5.4.1 Rules

- Exactly **one** cell is the **Active Audio Cell** at any time.
- Active audio routes to the HDMI sink.
- All other cells route to a null sink (muted but still playing — prevents stream buffering issues).
- When no cells have sources assigned, audio is silent.
- Default: the first cell with a source becomes active audio. Explicit selection overrides this.

#### 5.4.2 Implementation: PulseAudio-Compatible Routing

Use `pactl` commands for audio routing. This works on both PulseAudio and PipeWire (PulseAudio compatibility layer).

**Setup (on HomeView start):**

1. Create a null sink: `pactl load-module module-null-sink sink_name=homeview_mute`
2. Identify the HDMI output sink: `pactl list sinks short | grep hdmi`

**Per-cell audio routing:**

1. Find the sink-input for a Chromium instance by **matching PID**:
   ```
   pactl list sink-inputs | grep -A 20 "application.process.id = \"<chromium_pid>\""
   ```
2. Route active cell's sink-input to HDMI sink:
   ```
   pactl move-sink-input <sink_input_id> <hdmi_sink_name>
   ```
3. Route all other cells' sink-inputs to null sink:
   ```
   pactl move-sink-input <sink_input_id> homeview_mute
   ```

**Challenge: sink-input discovery timing.** Chromium may not create its audio stream immediately on launch. The audio router must:
- Poll for new sink-inputs when a cell launches a source (retry every 500ms, timeout 30s).
- Re-route when new sink-inputs appear (subscribe to PulseAudio events via `pactl subscribe`).
- Handle Chromium creating multiple sink-inputs per process (route all matching the PID).

**Audio switch latency target: ≤ 500ms** from API command receipt to sink routing change.

---

### 5.5 Control Server (FastAPI)

The control server exposes REST endpoints for idempotent control, a WebSocket for real-time updates, and serves the Remote PWA static assets.

#### 5.5.1 REST API (v1)

All endpoints require `Authorization: Bearer <token>` except pairing.

**Pairing:**

| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| POST | `/api/v1/pair` | `{ "pairing_code": "123456" }` | `{ "token": "...", "server_name": "..." }` |

**State:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/status` | Full state snapshot: layout, cells, sources, audio, health |

**Layouts:**

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/layouts` | — | List available layouts with cell definitions |
| PUT | `/api/v1/layout` | `{ "layout_id": "2x2" }` | Apply a layout (triggers transition) |

**Sources:**

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/sources` | — | List all sources |
| POST | `/api/v1/sources` | `{ "name": "...", "type": "url", "url": "..." }` | Add a custom source |
| PUT | `/api/v1/sources/{id}` | `{ "name": "...", "url": "..." }` | Update a source |
| DELETE | `/api/v1/sources/{id}` | — | Delete a custom source |

**Cells:**

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| PUT | `/api/v1/cells/{cell_id}/source` | `{ "source_id": "netflix" }` | Assign source to cell |
| DELETE | `/api/v1/cells/{cell_id}/source` | — | Clear cell (stop Chromium) |

**Audio:**

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| PUT | `/api/v1/audio/active` | `{ "cell_id": "main" }` | Set active audio cell |

**Presets:**

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/presets` | — | List saved presets |
| POST | `/api/v1/presets` | `{ "name": "Sunday Football" }` | Save current state as preset |
| PUT | `/api/v1/presets/{id}/apply` | — | Apply a preset |
| DELETE | `/api/v1/presets/{id}` | — | Delete a preset |

**Interactive Mode:**

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/interactive/start` | `{ "cell_id": "main" }` | Enable interaction for cell |
| POST | `/api/v1/interactive/stop` | — | Re-enforce kiosk mode |

**Server:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/server/info` | Server name, version, uptime, display resolution |
| GET | `/api/v1/server/health` | Health check: engine status, cell health, memory/CPU |

#### 5.5.2 WebSocket

- **Endpoint:** `GET /ws/control`
- Requires Bearer token as query param or first message.
- **Server -> Client events:**

| Event | Payload | Trigger |
|-------|---------|---------|
| `state.updated` | Full state snapshot | Any state change |
| `cell.health` | `{ cell_id, status, message }` | Cell crash/recovery |
| `pairing.complete` | `{ server_name }` | Successful pairing |

- **Client -> Server commands:** Same payloads as REST (convenience for real-time control).
- V1 sends full snapshots on every change. Diff events are a future optimization.

#### 5.5.3 Error Responses

Standard error format across all endpoints:

```json
{
  "error": {
    "code": "CELL_NOT_FOUND",
    "message": "Cell 'side4' does not exist in current layout",
    "details": {}
  }
}
```

HTTP status codes: 400 (bad request), 401 (unauthorized), 404 (not found), 409 (conflict — e.g., interactive mode already active), 500 (server error).

---

### 5.6 Remote Control PWA

A Progressive Web App served by the control server. Primary device: phone/tablet on the same LAN.

#### 5.6.1 Core Screens

**1. Pairing Screen**
- Input field for server URL (with mDNS discovery hint)
- Pairing code entry (6-digit)
- Success -> navigate to Control screen

**2. Control Screen (Main)**
- Visual representation of current layout with cells
- Each cell shows: source name/icon, status indicator (playing/empty/error)
- Tap a cell to: assign source, set as audio, clear
- Active audio cell visually highlighted (speaker icon)
- Layout switcher (bottom bar or swipe)

**3. Sources Screen**
- List of available sources with icons
- Add/edit/delete custom URLs
- Drag-and-drop to cells (stretch goal)

**4. Presets Screen**
- List of saved presets
- One-tap apply
- Save current layout as preset (name input)

**5. Settings Screen**
- Server info (name, IP, uptime)
- Reset pairing
- Interactive Mode toggle per cell

#### 5.6.2 PWA Requirements

| Requirement | Specification |
|-------------|--------------|
| Installable | Valid `manifest.json` with icons, start_url, display: standalone |
| Offline | Service worker caches shell; graceful "server unreachable" UX |
| Responsive | Mobile-first; usable on phone (360px+) and tablet (768px+) |
| Real-time | WebSocket connection for live state updates |
| Tech stack | Vanilla JS or lightweight framework (Preact/Alpine). No heavy build toolchain. |
| Performance | First paint < 1s on LAN. Bundle < 200KB gzipped. |

#### 5.6.3 Multi-Server Awareness

The PWA maintains a list of paired servers in localStorage. V1 supports connecting to one server at a time with a server-switcher dropdown. Full multi-server UX is a future goal.

---

## 6. Technical Constraints & Risks

### 6.1 DRM / Resolution Reality

| Service | Max Resolution on Linux | Reason |
|---------|------------------------|--------|
| Netflix | 480p-720p | Widevine L3 only (no TEE); Google policy |
| Amazon Prime Video | 720p | Widevine L3 only |
| ESPN | Up to 1080p | Generally no DRM restriction on browser |
| Generic URLs | Native resolution | No DRM involved |

**Why this can't be fixed:** Linux browsers get Widevine L3 because Google requires TEE-backed attestation (TPM + secure boot + hardened OS) for L1. Chrome OS gets L1 via its extensive integrity checking chain. No amount of Chromium flags or configuration changes this. This is a **hard constraint**, not a bug.

**Mitigation:** Document clearly. For users who need higher resolution, recommend dedicated streaming devices (Fire Stick, Roku) connected to HDMI inputs — HomeView can still manage the layout and switch between them in future versions.

### 6.2 Resource Pressure

| Configuration | Estimated RAM | Estimated CPU |
|---------------|--------------|---------------|
| 2 cells (side-by-side) | ~2-3 GB | ~20-30% (quad-core) |
| 4 cells (2x2) | ~4-6 GB | ~40-60% (quad-core) |
| 4 cells (hero + 3 side) | ~4-6 GB | ~40-60% (quad-core) |

**Minimum recommended hardware:** Quad-core x86_64, 8 GB RAM, hardware video decode (Intel/AMD integrated or discrete GPU).

**Chromium flags for resource reduction:**

```
--disable-gpu-compositing      # May help on low-end hardware
--disable-software-rasterizer  # Prefer GPU rendering
--js-flags="--max-old-space-size=256"  # Limit JS heap per instance
```

### 6.3 Streaming "Still Watching" Prompts

- Expected behavior on Netflix (after ~3 episodes), Prime (after ~5 hours), ESPN (varies).
- V1 does not auto-dismiss. Interactive Mode lets the operator intervene.
- The `cell.health` WebSocket event should detect when a cell's content stops updating (future: pixel-diff based stall detection).

### 6.4 Window Management Races

- Chromium creates windows asynchronously; initial geometry flags are hints.
- The engine **must** enforce geometry post-launch via X11 tools (see 5.1.2).
- A minimal or no window manager (bare X11 + Openbox with minimal config) reduces interference.

### 6.5 Audio Stack Variance

- PulseAudio vs PipeWire: `pactl` works on both via PipeWire's PA compatibility layer.
- The engine should detect the active audio server on startup and log it.
- If `pactl` commands fail, fall back to checking PipeWire-native tools (`pw-cli`) and log a warning.

### 6.6 Network Dependency

- All streaming sources require internet. HomeView does not cache or transcode content.
- Network interruptions affect individual cells independently. The engine should not restart cells during transient network issues (distinguish between process crash and content loading failure).

---

## 7. Core User Flows

### Flow 1: First-Time Setup

1. User installs HomeView on a Linux PC connected to their TV via HDMI.
2. User runs `homeview start` (or systemd service starts on boot).
3. TV displays pairing overlay: server name, IP, pairing code.
4. User opens the PWA URL on their phone.
5. User enters the 6-digit pairing code.
6. PWA confirms pairing. TV clears the overlay.
7. User is on the Control screen with an empty `single` layout.

### Flow 2: Setting Up a Multi-Stream View

1. User taps "Layout" and selects "2x2" (4 cells).
2. TV transitions from single to 2x2 (empty cells show a dark placeholder).
3. User taps cell 1, selects "ESPN" from sources.
4. Cell 1 launches ESPN in a Chromium window.
5. ESPN may prompt for cable provider login. User enables Interactive Mode for cell 1, logs in via keyboard/mouse on the server, then disables Interactive Mode.
6. User assigns Netflix to cell 2, Prime to cell 3, leaves cell 4 empty.
7. User taps cell 1's audio icon to set it as active audio.
8. The TV now shows ESPN (with audio) + Netflix + Prime in a 2x2 grid.

### Flow 3: Quick Preset Switch

1. User opens Presets screen, taps "Sunday Football" preset.
2. HomeView loads the preset: hero_3side layout, ESPN in hero, RedZone in side1, Fantasy dashboard in side2, side3 empty.
3. Audio activates on the hero (ESPN) cell.
4. Total time from tap to all cells rendering: ≤ 5 seconds (video load time varies by service).

### Flow 4: Handling a Cell Crash

1. Netflix cell crashes (Chromium process exits).
2. Engine detects the exit within 1 second.
3. PWA receives `cell.health` event showing cell status as `restarting`.
4. Engine restarts Chromium with the same Netflix URL and profile.
5. Window geometry is re-enforced.
6. Audio routing is restored if this was the active audio cell.
7. PWA receives `cell.health` event showing cell status as `running`.
8. Total recovery time: ≤ 10 seconds.

---

## 8. Preset System

### 8.1 Preset Schema

```json
{
  "id": "sunday-football",
  "name": "Sunday Football",
  "layout_id": "hero_3side",
  "cell_assignments": {
    "main": "espn",
    "side1": "redzone",
    "side2": "fantasy-dashboard",
    "side3": null
  },
  "active_audio_cell": "main",
  "created_at": "2026-04-12T14:00:00Z"
}
```

### 8.2 Preset Application

When a preset is applied:
1. Switch to the preset's layout (triggers layout transition rules from 5.2.3).
2. Assign sources to cells per `cell_assignments`. Null entries clear the cell.
3. Set the active audio cell.
4. If a source in the preset has been deleted, skip that assignment and log a warning.

---

## 9. Development Phases

### Phase 1 — Core Engine + Pairing (Weeks 1-3)

**Deliverables:**
- Composition engine launches N cells in 2x2 layout
- Source registry (SQLite) with pre-loaded ESPN/Prime/Netflix
- Assign source to cell via REST API
- Pairing overlay on TV + token auth
- HDMI-only audio selection (active cell via pactl)
- Minimal Remote PWA: pair + control screen + assign sources + switch audio

**Exit Criteria:**
- [ ] 2x2 layout works reliably with 4 Chromium windows
- [ ] ESPN, Prime, Netflix can be opened and kept running in cells
- [ ] Remote PWA can pair and control sources/audio
- [ ] Audio switches between cells within 500ms
- [ ] Single cell crash recovers automatically within 10 seconds

### Phase 2 — Layout System + Presets + Interactive Mode (Weeks 4-6)

**Deliverables:**
- Layout templates from JSON (single, side_by_side, 2x2, hero_3side, pip)
- Deterministic layout switching with source preservation
- Preset save/load/apply
- Interactive Mode enable/disable per cell
- PWA: layout switcher, presets screen, interactive mode toggle

**Exit Criteria:**
- [ ] All 5 layouts render correctly at 1080p and 4K
- [ ] Switching layouts preserves source assignments per rules
- [ ] One-tap preset loads a multi-cell configuration reliably
- [ ] Interactive Mode allows manual login on a streaming service

### Phase 3 — Reliability Hardening (Weeks 7-8)

**Deliverables:**
- Watchdog with exponential backoff and crash-loop detection
- Health reporting to PWA via WebSocket events
- Memory/CPU monitoring and logging
- Display resolution change handling
- Startup self-checks (X11, pactl, Chromium binary, HDMI sink)

**Exit Criteria:**
- [ ] Runs 8 hours unattended with 4 cells under normal home network
- [ ] Cell crash recovery verified under all layouts
- [ ] PWA shows real-time cell health status
- [ ] System survives display resolution change without manual restart

---

## 10. Success Criteria (v1, Testable)

| # | Criterion | Measurement | Target |
|---|-----------|------------|--------|
| 1 | **Pairing** | First-run: TV shows overlay, PWA pairs successfully | 100% success on LAN |
| 2 | **Control** | Remote can switch layouts and assign sources | All API endpoints functional |
| 3 | **Preset speed** | Time from preset apply to all cells loaded | ≤ 5 seconds (video playback depends on service) |
| 4 | **Audio switching** | Time from API command to sink routing change | ≤ 500ms |
| 5 | **Crash recovery** | Single Chromium crash to full cell restoration | ≤ 10 seconds |
| 6 | **Unattended runtime** | 4 cells running without manual intervention | ≥ 8 hours |
| 7 | **Resource ceiling** | 4-cell 2x2 RAM usage | ≤ 8 GB total system |
| 8 | **PWA load** | First meaningful paint on LAN | < 1 second |

---

## 11. Project Structure

```
homeview/
├── server/
│   ├── main.py                  # Entry point, FastAPI app
│   ├── composition/
│   │   ├── engine.py            # Core engine: cell lifecycle, layout management
│   │   ├── cell.py              # Cell class: Chromium process wrapper
│   │   ├── layout.py            # Layout loading, geometry computation
│   │   ├── window.py            # X11 window placement and enforcement
│   │   └── health.py            # Health monitoring, crash detection, backoff
│   ├── audio/
│   │   └── router.py            # PulseAudio routing via pactl
│   ├── sources/
│   │   └── registry.py          # Source CRUD, SQLite persistence
│   ├── api/
│   │   ├── routes.py            # REST endpoint definitions
│   │   ├── websocket.py         # WebSocket handler
│   │   └── pairing.py           # Pairing flow
│   ├── auth/
│   │   └── tokens.py            # Bearer token generation/validation
│   ├── presets/
│   │   └── manager.py           # Preset save/load/apply
│   ├── db.py                    # SQLite connection and schema
│   └── config.py                # Configuration (paths, defaults, env vars)
├── remote/
│   ├── index.html               # PWA shell
│   ├── app.js                   # Main application logic
│   ├── style.css                # Styles (mobile-first)
│   ├── manifest.json            # PWA manifest
│   └── sw.js                    # Service worker
├── layouts/
│   ├── single.json
│   ├── side_by_side.json
│   ├── 2x2.json
│   ├── hero_3side.json
│   └── pip.json
├── scripts/
│   ├── install.sh               # Installation script
│   └── homeview.service         # systemd unit file
├── tests/
│   ├── test_engine.py
│   ├── test_audio.py
│   ├── test_api.py
│   ├── test_layout.py
│   └── test_presets.py
├── pyproject.toml               # Python project config
└── README.md
```

---

## 12. Research Findings

Research conducted via web search (Standard tier) on 2026-04-12.

### Key Findings

- **No consumer competitor exists.** Commercial video wall software (Polywall, Userful) costs $1K+/display and targets enterprise. Anthias (open-source signage) handles single-source rotation, not multi-stream. OBS isn't designed for always-on headless operation. HomeView occupies a genuine whitespace.

- **Chromium `--kiosk` breaks window geometry.** [Stack Overflow](https://stackoverflow.com/questions/49257397) confirms `--kiosk` forces fullscreen and ignores `--window-size`/`--window-position`. The solution is `--app=<url>` mode with X11 enforcement post-launch.

- **Widevine L3 is a hard ceiling on Linux.** [Reddit r/linux discussion](https://www.reddit.com/r/linux/comments/11l9v4e/) provides detailed technical analysis: Google's Widevine binary performs TEE attestation, OS integrity checks, and trusted boot validation. Linux gets L3 (480-720p) because it lacks Chrome OS's hardware-backed security chain. This is Google policy, not a technical limitation that can be worked around.

- **PulseAudio routing works on PipeWire.** PipeWire's PulseAudio compatibility layer supports `pactl` commands including `move-sink-input`. Per-PID sink-input matching is the standard approach for routing audio from specific application instances.

- **X11 window placement is mature.** `xdotool` and `wmctrl` are the standard tools. Race conditions with async window creation are a known challenge — PID-based polling is the standard solution.

### Sources

- [Stack Overflow: Chromium kiosk mode window positioning](https://stackoverflow.com/questions/49257397)
- [Reddit: Widevine L3 on Linux technical analysis](https://www.reddit.com/r/linux/comments/11l9v4e/)
- [ArchWiki: PipeWire](https://wiki.archlinux.org/title/PipeWire)
- [PipeWire PulseAudio Integration Guide](https://www.benashby.com/resources/pipewire-pulseaudio-integration/)
- [xdotool GitHub](https://github.com/jordansissel/xdotool)
- [Anthias (open-source digital signage)](https://anthias.screenly.io/)

---

## 13. Key Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Chromium window mode | `--app` (not `--kiosk`) | `--kiosk` ignores window geometry — confirmed by research |
| Audio control tool | `pactl` (prescribed) | Clear winner: works on PulseAudio AND PipeWire via compat layer |
| X11 window tool | Open (xdotool/wmctrl or python-xlib) | Both viable; no clear winner. Implementer chooses. |
| Persistence | SQLite | Zero-config, sufficient for single-operator. No need for PostgreSQL/Redis. |
| DRM approach | Accept 480-720p limitation | Hard constraint (Widevine L3). Document clearly, don't over-promise. |
| PWA framework | Lightweight (Vanilla/Preact/Alpine) | No heavy build toolchain for what's essentially a remote control |
| v1 scope | No Sonos, no multi-TV | Keep shippable. Sonos is the top v2 priority. |

---

## 14. v2+ Roadmap: Sonos Integration

### 14.1 Vision

Extend HomeView's audio beyond HDMI to Sonos wireless speakers. Any cell's audio can route to any Sonos speaker or group. The PWA becomes a unified audio control surface.

### 14.2 Architecture

```
+--------------------------------------+
|           HomeView Server            |
|                                      |
|  Cell Audio --> Icecast Server ------|-----> Sonos Speaker(s)
|              (HTTP stream)           |       (via HTTP streaming)
|                                      |
|  Cell Audio --> HDMI Sink            |-----> TV Speakers
|              (PulseAudio)            |
+--------------------------------------+
```

**Pipeline:** PulseAudio/PipeWire captures cell audio -> encodes to MP3/OGG -> streams via Icecast -> Sonos plays the Icecast stream URL.

### 14.3 Key Components

| Component | Purpose | Technology |
|-----------|---------|-----------|
| Audio Capture | Tap audio from a cell's PulseAudio stream | PulseAudio monitor source or `parec` |
| Icecast Server | HTTP audio streaming endpoint | Icecast2 (self-hosted, lightweight) |
| Sonos Discovery | Find Sonos speakers on LAN | SSDP/UPnP discovery (python-soco library) |
| Sonos Control | Play/pause, volume, grouping | SoCo Python library (mature, well-maintained) |
| PWA Audio UI | Speaker selection, volume, grouping | Extended audio panel in Remote PWA |

### 14.4 Audio Routing (v2)

| Routing Mode | Description |
|-------------|-------------|
| HDMI only (v1) | Active cell -> HDMI sink. All others muted. |
| Sonos only | Active cell -> Icecast -> Sonos group. HDMI muted. |
| HDMI + Sonos | Active cell -> both HDMI and Icecast/Sonos simultaneously. |
| Multi-zone | Different cells -> different Sonos speakers. (Stretch goal) |

### 14.5 Latency Considerations

- Sonos adds 70-200ms latency due to buffering.
- HDMI audio is near-instantaneous.
- **HDMI + Sonos will not be in sync.** This is expected behavior — Sonos has inherent buffering latency. Options:
  - Accept the delay (fine for ambient viewing in another room).
  - Add a configurable HDMI audio delay to sync with Sonos (complex, stretch goal).
  - Recommend HDMI ARC/eARC from TV to Sonos soundbar as the low-latency alternative.

### 14.6 Scope (v2)

**In scope:**
- Sonos speaker discovery and listing in PWA
- Route active cell audio to a Sonos speaker/group via Icecast
- Volume control per speaker from PWA
- Speaker grouping from PWA

**Out of scope (v2):**
- Multi-zone (different cells to different speakers) — deferred to v3
- A/V sync compensation
- Sonos as primary audio (bypassing HDMI entirely) for DRM content

### 14.7 ARC/eARC Alternative

Many Sonos soundbars support HDMI ARC/eARC from the TV. This provides:
- Zero-config audio from TV speakers to Sonos soundbar
- Lower latency than Icecast streaming
- No HomeView software involvement

**Recommendation:** Document ARC/eARC as the "easy mode" for Sonos users. The Icecast pipeline is for multi-room scenarios where different rooms get different cell audio.

---

## 15. v2+ Roadmap: Future Phases (Brief)

### Phase 4 — Sonos Integration (see Section 14)

Estimated scope: 3-4 weeks. Requires Icecast, python-soco, extended PWA audio panel.

### Phase 5 — Multi-TV Orchestration

- One PWA controlling multiple HomeView server instances.
- Move sources between TVs.
- Shared presets across servers.
- Synchronized layouts (e.g., all TVs switch to hero on a big play).

### Phase 6 — Smart Automation

- Scheduled presets (cron-like: "Sunday Football at noon").
- Sports API integration for event-driven layout changes.
- Auto-dismiss "still watching" prompts (per-service, best-effort).
- Voice control integration (Home Assistant / Alexa skill).

### Phase 7 — Wayland Support

- Port window management from X11 to Wayland compositor protocols.
- Requires a Wayland compositor that supports programmatic window placement (wlr-layer-shell or custom compositor).
- Will likely require Cage or a custom wlroots-based compositor.

---

## 16. Open Questions (Deferred)

| Question | Context | Phase |
|----------|---------|-------|
| VNC/noVNC for Interactive Mode | Would let users interact with cells from the PWA instead of needing physical access to the server | v2 |
| Per-source profile vs per-cell profile | Should Chromium profiles be tied to source identity (Netflix profile = Netflix logins) or cell position? | v1 implementation detail |
| Automated "still watching" dismissal | Per-service DOM injection scripts. Brittle but high-value. | v3 |
| Hardware video decode optimization | VA-API / VDPAU configuration for lower CPU usage with multiple streams | v1 stretch |
| Multi-TV UX patterns | How to present multiple servers in the PWA without overwhelming the operator | v2 |
| Sonos + HDMI sync compensation | Configurable audio delay on HDMI to match Sonos buffering | v3 |
