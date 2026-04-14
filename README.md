# homeviewx11

A self-hosted multi-stream video wall controller. HomeView manages multiple Chromium instances on a single X11 display, arranging them into configurable layouts and presenting a unified HDMI output — no video mixer hardware required.

## What it does

- Launches and positions Chromium windows on an X11 display using configurable layout grids
- Exposes a REST + WebSocket API for remote control from a companion app or any HTTP client
- Manages named **sources** (streaming URLs), **layouts**, and **presets** (saved configurations)
- Routes PulseAudio to whichever cell is "active" for audio
- Supports an **interactive mode** that temporarily unlocks a cell for direct user input
- Runs as a systemd service on a headless/dedicated Linux machine

## Architecture

```
FastAPI server (uvicorn)
├── CompositionEngine       — orchestrates cells, windows, audio routing
│   ├── LayoutManager       — loads JSON layout files, computes pixel geometry
│   ├── Cell                — wraps a Chromium subprocess per cell
│   ├── WindowManager       — X11 window positioning via python-xlib
│   ├── AudioRouter         — PulseAudio sink routing
│   ├── HealthMonitor       — watches for crashed cells
│   └── InteractiveManager  — exclusive input focus for one cell
├── SourceRegistry          — CRUD for streaming sources (aiosqlite)
├── PresetManager           — save/apply named layout+source configurations
├── Auth (pairing + tokens) — 6-digit pairing code → Bearer token flow
└── EventBus / WebSocket    — real-time state push to connected clients
```

**Tech stack:** Python 3.12+, FastAPI, uvicorn, aiosqlite (SQLite), pydantic-settings, python-xlib

## Built-in layouts

| ID | Name | Cells |
|----|------|-------|
| `single` | Single fullscreen | 1 |
| `side_by_side` | Side by Side | 2 |
| `pip` | Picture-in-Picture | 2 (hero + pip) |
| `hero_3side` | Hero + 3 Side | 4 (hero + 3 side) |
| `2x2` | 2×2 Grid | 4 |

Custom layouts are JSON files in `layouts/` — see `layouts/2x2.json` for the schema.

## API overview (all routes require Bearer token except pairing)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/server/health` | Liveness check (public) |
| `GET` | `/api/v1/pair/code` | Get current pairing code (public) |
| `POST` | `/api/v1/pair` | Submit code → receive token (public) |
| `GET` | `/api/v1/server/info` | Server name, version, mock mode |
| `GET` | `/api/v1/status` | Current layout, cells, audio state |
| `GET/PUT` | `/api/v1/layout` | List layouts / apply a layout |
| `GET/POST/PUT/DELETE` | `/api/v1/sources` | CRUD for streaming sources |
| `PUT/DELETE` | `/api/v1/cells/{i}/source` | Assign or clear a cell's source |
| `PUT` | `/api/v1/audio/active` | Set active audio cell |
| `GET/POST/PUT/DELETE` | `/api/v1/presets` | Save/apply/delete presets |
| `POST` | `/api/v1/interactive/start` | Enter interactive mode for a cell |
| `POST` | `/api/v1/interactive/stop` | Exit interactive mode |
| `WS` | `/ws/control?token=…` | Real-time state + events stream |

## Setup

### Prerequisites

- Linux with an X11 display (`:0` by default)
- Chromium installed (`chromium-browser` on PATH, or set `HOMEVIEW_CHROMIUM_BINARY`)
- Python 3.12+ and [uv](https://github.com/astral-sh/uv)

### Install and run

```bash
git clone <repo> && cd homeviewx11
uv sync
uv run homeview
```

Server starts at `http://0.0.0.0:8000`.

On first boot, a 6-digit pairing code is printed to stdout (and available at `GET /api/v1/pair/code`). Submit it to `POST /api/v1/pair` to receive a Bearer token.

### Configuration (environment variables / `.env` file)

All variables use the `HOMEVIEW_` prefix.

| Variable | Default | Description |
|----------|---------|-------------|
| `HOMEVIEW_HOST` | `0.0.0.0` | Bind address |
| `HOMEVIEW_PORT` | `8000` | HTTP port |
| `HOMEVIEW_SERVER_NAME` | hostname | Display name in `/server/info` |
| `HOMEVIEW_DB_PATH` | `~/.homeview/homeview.db` | SQLite database path |
| `HOMEVIEW_PROFILES_DIR` | `~/.homeview/profiles` | Chromium profile directories |
| `HOMEVIEW_LAYOUTS_DIR` | `layouts/` | Directory of layout JSON files |
| `HOMEVIEW_CHROMIUM_BINARY` | `chromium-browser` | Chromium executable |
| `HOMEVIEW_DISPLAY` | `:0` | X11 display |
| `HOMEVIEW_MOCK` | `0` | `1` to run without real X11/Chromium |

### Mock mode (development / CI)

Set `HOMEVIEW_MOCK=1` to run the full server without X11 or Chromium. All API endpoints and WebSocket events work normally; window management and process launching are stubbed.

```bash
HOMEVIEW_MOCK=1 uv run homeview
```

### systemd service

```bash
sudo cp scripts/homeview.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now homeview
```

See `scripts/homeview.service` for expected user/paths (`/opt/homeview`, `/var/lib/homeview`).

### Reset pairing

```bash
uv run homeview-reset-pairing
```

Revokes all tokens and prints a new 6-digit pairing code.

## Development

```bash
uv sync --all-extras
uv run pytest -q                              # run tests
uv run pytest -q --cov=server --cov-fail-under=80  # with coverage
ruff format .                                 # format
ruff check . --fix                            # lint
```

### Project structure

```
server/
  main.py          — app factory (create_app)
  config.py        — pydantic-settings (Settings)
  models.py        — Pydantic domain models
  db.py            — aiosqlite helpers + schema init
  cli.py           — homeview / homeview-reset-pairing entry points
  api/
    routes.py      — all REST endpoints
    websocket.py   — /ws/control WebSocket handler
    events.py      — in-process EventBus
    dependencies.py — FastAPI Depends helpers
  auth/
    pairing.py     — 6-digit code flow
    tokens.py      — Bearer token issuance + validation
    middleware.py  — auth dependency factory
  composition/
    engine.py      — CompositionEngine (central coordinator)
    layout.py      — LayoutManager, geometry, transitions
    cell.py        — Cell + ChromiumLauncher abstraction
    window.py      — WindowManager (X11 via python-xlib)
    display.py     — display resolution detection
    audio.py       — AudioRouter (PulseAudio)
    health.py      — HealthMonitor
    interactive.py — InteractiveManager
  sources/
    registry.py    — SourceRegistry (DB-backed CRUD)
  presets/
    manager.py     — PresetManager (save/apply configurations)
layouts/           — JSON layout definitions
tests/             — pytest suite (mock mode, async)
scripts/           — systemd service unit
docs/
  prd/             — product requirements
  plans/           — implementation plans
```

## License

See [LICENSE](LICENSE).
