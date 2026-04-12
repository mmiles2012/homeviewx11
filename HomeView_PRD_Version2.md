# HomeView — Multi-Stream Video Wall Controller
## Product Requirements Document v1.1 (Refined)

---

## 1. Overview

HomeView is a **self-hosted** system that turns any TV into a sports-bar-style multi-stream display. A Linux server composites multiple streaming and web video sources into configurable layouts, outputting a **single HDMI signal** to a TV. The TV behaves as a “dumb” display: it only shows HDMI input. A phone/tablet Progressive Web App (PWA) is the primary control interface.

### Core Principles

- **Transparent to the TV.** The display can be completely “dumb”: HDMI in, picture out.
- **Server as the brain.** All window composition, source management, and audio selection happen server-side.
- **Single operator (v1).** One household operator controls the system; no multi-user permissions in v1.
- **Sports-first latency.** Prefer low-latency and reliability over pixel-perfect composition when tradeoffs arise.
- **Manual intervention is acceptable.** Some streaming services may require occasional manual interaction (login prompts, “still watching”).

---

## 2. V1 Scope, Non-Goals, and Definitions

### 2.1 V1 Scope (What we will build)

In v1, HomeView provides:

1. A **Composition Engine** that launches and manages multiple Chromium “cells” (windows) positioned into a layout.
2. A **Control Server** (FastAPI) exposing REST + WebSocket APIs.
3. A **Remote Control PWA** served by the server for configuration and control.
4. A **Source Registry** for known streaming/web sources.
5. **HDMI-only audio**: select exactly one cell as the active audio source; all others muted.

### 2.2 Non-Goals (v1)

To keep v1 shippable, the following are explicitly out of scope:

- Sonos control (discovery, grouping, Icecast streaming).  
  *Note:* Sonos may still work **out-of-band** via HDMI ARC/eARC from the TV.
- Multi-output (one server driving multiple TVs from one instance).
- Multi-user accounts, roles, or permissions beyond a single paired remote.
- Automated streaming-service login flows or “still watching” dismissal.
- Perfect A/V sync across external audio devices.
- Input forwarding (CEC/IR/remote) to streaming services.

### 2.3 Supported Services (v1)

Initial supported services:

- **ESPN**
- **Amazon Prime Video**
- **Netflix**

**Definition of “supported” in v1:**
- HomeView can launch the service URL in a Chromium cell, maintain a persistent profile for that cell, keep it positioned correctly, and restart it if it crashes.
- The user may need to log in or respond to prompts manually via **Interactive Mode**.
- HomeView does **not** guarantee maximum resolution, HDR, or 4K playback, especially for DRM services on Linux.

### 2.4 Key Terms

- **Server Instance:** One HomeView deployment controlling exactly **one HDMI display output** (v1).
- **Cell:** One Chromium process/window controlled by HomeView and placed into a layout region.
- **Layout:** A template describing regions (cells) within a 1.0 × 1.0 coordinate space.
- **Source:** A named streaming/web target (URL + metadata) assignable to a cell.
- **Preset:** A saved configuration: layout + cell→source assignments + active-audio cell.

---

## 3. System Architecture (v1)

```
┌─────────────────────────────────────────────────┐
│                  Linux Server                    │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │         Composition Engine (Python)       │   │
│  │  - Launch/manage Chromium per cell        │   │
│  │  - Compute geometry from layout           │   │
│  │  - Enforce window placement (X11)         │   │
│  │  - Watchdog / restart                     │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  ���            Control Server (FastAPI)       │   │
│  │  - REST + WebSocket                       │   │
│  │  - Pairing + auth token                   │   │
│  │  - Serves Remote PWA                      │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │     Audio Control (PulseAudio-compatible) │   │
│  │  - Exactly one active audio cell → HDMI   │   │
│  │  - All other cells muted (null sink)      │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
└───────────────┬─────────────────────────────────┘
                │ LAN (HTTPS/WS)
                ▼
         ┌───────────────┐
         │ Phone / Tablet │
         │ Remote PWA     │
         └───────────────┘
                │ HDMI
                ▼
           ┌─────────┐
           │   TV    │
           └─────────┘
```

### 3.1 V1 Atomic Unit: One Server Instance → One TV Output

- A HomeView server instance drives exactly one display output (one TV) in v1.
- Multi-TV households run multiple server instances (e.g., multiple small PCs), and the Remote PWA can control multiple instances.

---

## 4. Pairing, Security, and Setup UX (v1)

HomeView is LAN-oriented, but **must not** be open/uncontrolled on the network.

### 4.1 Pairing Mode (first-run)

On first boot (or after reset), HomeView enters **Pairing Mode**:

- The TV shows a minimal overlay:
  - Server name (default: hostname)
  - IP address / `.local` hostname (best effort)
  - A short-lived **6-digit pairing code**
- The Remote PWA connects to the server and submits the pairing code.
- On success, server issues a long-lived **Bearer token** to the remote.

### 4.2 Authentication Model

- All REST endpoints and WebSocket connections require:
  - `Authorization: Bearer <token>`
- Token is stored server-side (single operator, v1).
- Remote stores token locally (browser storage).

### 4.3 Reset / Re-pair

- A local command (or deleting a token file) resets pairing, forcing Pairing Mode on next start.
- The reset mechanism must be documented and requires local access to the server.

### 4.4 Interactive Mode (manual login/prompts)

Some services require manual interaction. HomeView supports **Interactive Mode**:

- When enabled, the system temporarily allows user interaction for a chosen cell (or dedicated setup cell).
- V1 requirement: at minimum, Interactive Mode must support a “pause kiosk enforcement” strategy sufficient to log in (implementation-specific).
- Future: optional VNC/noVNC integration can be added later; not required in v1.

---

## 5. Component Specifications

## 5.1 Composition Engine (Python)

The core Python process that manages the lifecycle of all cells on the display.

**Responsibilities:**
- Launch/kill Chromium instances per cell with correct geometry and isolated profiles
- Apply layout templates by computing pixel positions from proportional definitions
- Handle layout transitions deterministically
- Monitor Chromium health (restart crashed instances with backoff)
- Expose state to the Control Server (for `/status` and WS events)

### 5.1.1 Cell Launching

Each cell is a Chromium process launched via subprocess:

- Kiosk-like mode for a “TV appliance” feel
- `--user-data-dir` is persistent per cell (or per source if configured) so logins persist

Example launch shape (illustrative):

```
chromium-browser \
  --kiosk \
  --window-position=0,0 \
  --window-size=960,540 \
  --no-first-run \
  --disable-infobars \
  --autoplay-policy=no-user-gesture-required \
  --user-data-dir=/var/lib/homeview/profiles/cell-c1 \
  --app=https://www.espn.com/watch
```

### 5.1.2 Window Placement & Determinism

The engine must:
- Reliably bind **cell → window** (store a window identifier per cell)
- Enforce geometry after launch (to handle race conditions)
- Remove decorations and keep windows topmost as required

Implementation can use X11 tools (`xdotool`, `wmctrl`) and/or X11 libraries; Wayland is not a v1 target.

### 5.1.3 Health Monitoring & Restart

Minimum v1 behavior:
- Detect Chromium exit/crash per cell
- Restart with exponential backoff if crash-looping
- Restore last assigned source URL after restart

---

## 5.2 Layout System

Layouts are defined as JSON files specifying proportional cell regions within a 1.0 × 1.0 coordinate space.

Each cell definition includes:
- `id` (stable string)
- geometry (`x`, `y`, `w`, `h`)
- optional `role`: `hero`, `side`, `grid`, `pip`

Example:

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

### 5.2.1 Included Layouts (v1)

- `single` (1 cell)
- `2x2` (4 cells)
- `hero_3side` (4 cells)
- `pip` (2 cells, one overlay)

*(3x3 can remain a stretch goal; it increases resource pressure and window-management complexity.)*

### 5.2.2 Deterministic Layout Switching Rules

When switching layouts, HomeView preserves sources deterministically:

1. Map `hero` → `hero` (if present in both layouts).
2. Map `side` cells in stable order (top-to-bottom, left-to-right).
3. Map remaining cells in stable order.
4. If new layout has fewer cells:
   - drop lowest-priority roles first (`grid`, then `side`)
   - never drop `hero` unless new layout has no `hero`
5. If new layout has more cells:
   - new cells start empty

---

## 5.3 Source Registry

A persistent store of sources (JSON or SQLite).

Schema (minimum):

```json
{
  "id": "netflix",
  "name": "Netflix",
  "type": "streaming",
  "url": "https://www.netflix.com",
  "requires_widevine": true,
  "notes": "Login via Interactive Mode; resolution may be limited on Linux."
}
```

### 5.3.1 Source Types (v1)

- `streaming` (ESPN, Prime, Netflix)
- `url` (generic web pages)

---

## 5.4 Audio (v1: HDMI-only)

Audio is intentionally simple in v1 to ensure reliability.

### 5.4.1 Rules

- Exactly **one** cell is the **Active Audio Cell** at any time (when at least one cell has a source).
- Active audio routes to the HDMI sink.
- All other cells route to a null sink (muted).

### 5.4.2 Implementation Requirement

- Use **PulseAudio-compatible** control (e.g., `pactl`) so this works on PulseAudio and PipeWire (PulseAudio compatibility) systems.
- The engine must deterministically identify the audio stream(s) belonging to each Chromium cell.

---

## 5.5 Control Server (FastAPI)

The control server exposes REST endpoints for idempotent control and a WebSocket for real-time updates. It also serves the Remote PWA static assets.

### 5.5.1 REST Endpoints (v1)

**Pairing**
- `POST /api/v1/pair`  
  Body: `{ "pairing_code": "123456" }`  
  Response: `{ "token": "..." }`

**State**
- `GET /api/v1/status` — returns full current state snapshot

**Layouts**
- `GET /api/v1/layouts` — list available layouts
- `PUT /api/v1/layout` — apply a layout  
  Body: `{ "layout_id": "2x2" }`

**Sources**
- `GET /api/v1/sources`
- `POST /api/v1/sources` — add/update (single-operator; can be simple CRUD)

**Cells**
- `PUT /api/v1/cells/{cell_id}/source`  
  Body: `{ "source_id": "netflix" }`

**Audio**
- `PUT /api/v1/audio/active`  
  Body: `{ "cell_id": "main" }`

**Interactive Mode**
- `POST /api/v1/interactive/start`  
  Body: `{ "cell_id": "main" }`
- `POST /api/v1/interactive/stop`

### 5.5.2 WebSocket (v1)

- `GET /ws/control`
  - Client sends commands (same payloads as REST)
  - Server emits `state.updated` events containing either:
    - full snapshot (simplest v1), or
    - diff events (optional later optimization)

---

## 5.6 Remote Control App (PWA)

A PWA served by the control server. Primary device is phone/tablet on the same LAN.

**Key features (v1):**
- Pair to a server (enter pairing code)
- Show current layout + cells
- Select a cell, assign a source (ESPN/Prime/Netflix + generic URL)
- Select active audio cell
- Switch layouts (single/2x2/hero_3side/pip)
- Save/load presets (optional v1, but strongly recommended)

**Remote UX note:** Because multi-server support is desired eventually, the Remote PWA should keep a list of paired servers.

---

## 6. Technical Constraints & Risks (v1)

### 6.1 DRM / Resolution Reality

- Netflix and Prime may be limited in resolution on Linux browsers due to DRM constraints.
- This is acceptable in v1; document it clearly as a known limitation.

### 6.2 Streaming Prompts / “Still Watching”

- Expected behavior; v1 does not guarantee auto-dismissal.
- Interactive Mode exists to let the operator intervene when needed.

### 6.3 Window Management Races

- Chromium may create windows asynchronously; geometry enforcement must be robust.
- The engine must be prepared to re-apply geometry and re-bind window IDs after restarts.

### 6.4 OS Audio Stack Variance

- Some systems use PulseAudio; others use PipeWire with PulseAudio compatibility.
- HomeView controls audio via PulseAudio-compatible tools, not by tightly coupling to one distro version.

---

## 7. Development Phases (Updated)

### Phase 1 — Single TV, Core Engine + Pairing (Weeks 1-3)

- Composition engine launches N cells in 2x2
- Source registry + assign source to cell
- Pairing overlay + token auth
- HDMI-only audio selection (active cell)
- Minimal Remote PWA (pair + assign sources + switch active audio)

**Exit criteria:**
- 2x2 works reliably; Netflix/Prime/ESPN can be opened and kept running
- Remote can pair and control sources/audio

### Phase 2 — Layout System + Presets + Interactive Mode (Weeks 4-6)

- Layout templates from JSON (single, 2x2, hero_3side, pip)
- Deterministic layout switching preservation rules
- Presets (save/load)
- Interactive Mode control endpoints + minimal UX to enable/disable it

**Exit criteria:**
- One-tap preset loads a multi-cell configuration reliably

### Phase 3 — Reliability Hardening (Weeks 7-8)

- Watchdog + restart backoff
- Better state reporting and instrumentation
- Memory/CPU monitoring
- Stress testing with longer runtimes

**Exit criteria:**
- Runs 8 hours unattended with 4 cells under normal home network conditions

*(Sonos and multi-TV orchestration can be Phase 4+.)*

---

## 8. Success Criteria (v1, testable)

1. **Pairing:** On first run, the TV shows a pairing overlay and the Remote PWA can pair successfully.
2. **Control:** Remote can switch layouts and assign ESPN/Prime/Netflix sources to cells.
3. **Preset speed:** Applying a preset results in the correct layout + URLs loaded in **≤ 5 seconds** on a typical home LAN (video playback time depends on service).
4. **Audio:** Switching active audio cell results in HDMI audio switching within **≤ 500 ms** from command receipt to sink routing change.
5. **Reliability:** With 4 cells running, the system operates for **≥ 8 hours** without manual intervention, and any single Chromium crash recovers automatically within **≤ 10 seconds**.

---

## 9. Project Structure (Proposed)

```
homeview/
├── server/
│   ├── main.py
│   ├── composition/
│   │   ├── engine.py
│   │   ├── cell.py
│   │   ├── layout.py
│   │   └── display.py
│   ├── audio/
│   │   └── router.py
│   ├── sources/
│   │   ├── registry.py
│   │   └── sources.json
│   ├── api/
│   │   ├── rest.py
│   │   ├── websocket.py
│   │   └── pairing.py
│   ├── auth/
│   │   └── tokens.py
│   ├── presets/
│   │   ├── manager.py
│   │   └── presets.json
│   └── config.py
├── remote/
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   └── manifest.json
├── layouts/
│   ├── single.json
│   ├── 2x2.json
│   ├── hero_3side.json
│   └── pip.json
├── scripts/
│   ├── install.sh
│   └── homeview.service
├── requirements.txt
└── README.md
```

---

## 10. Open Questions (Explicitly deferred)

- Best-in-class approach for Interactive Mode (VNC vs local keyboard/mouse vs temporary non-kiosk window)
- Automated “still watching” handling per service (likely service-specific and brittle)
- Multi-TV orchestration UX (one remote controlling many servers seamlessly)
- Sonos integration approach (ARC-first vs streaming pipeline)

---