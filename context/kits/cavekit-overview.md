---
created: "2026-04-19T00:00:00Z"
last_edited: "2026-04-19T00:00:00Z"
---

# Cavekit Overview

## Project

**HomeView v1 PWA + Server Gaps** — Self-hosted multi-stream video wall controller. Adds a React PWA companion app (pair, control layouts/cells/sources/audio/presets, interactive mode, live WebSocket state) and closes four server-side gaps deferred from the v1-server spec.

## Domain Index

| Domain | Cavekit File | Requirements | Status | Description |
|--------|-------------|--------------|--------|-------------|
| server-gaps | cavekit-server-gaps.md | 4 | DRAFT | Four server-side Python fixes: pairing error envelope, cell.health WS events, TV overlay, static + CORS |
| pwa-scaffold | cavekit-pwa-scaffold.md | 5 | DRAFT | Vite+React+TS project, service worker, manifest, Vite proxy, typed API client, production build integration |
| pwa-state | cavekit-pwa-state.md | 4 | DRAFT | App state shape, pure reducer, WebSocket hook with exponential backoff, context provider |
| pwa-screens | cavekit-pwa-screens.md | 8 | DRAFT | 8 UI screens: Pair, Main/Status, Source Picker, Layout Picker, Audio, Presets, Interactive, Settings |
| pwa-tests | cavekit-pwa-tests.md | 5 | DRAFT | Vitest unit tests for reducer, API client, WS hook; 80% coverage threshold |

## Cross-Reference Map

| Domain A | Interacts With | Interaction Type |
|----------|---------------|-----------------|
| server-gaps | pwa-scaffold | Provides CORS headers and static file serving (R4) |
| server-gaps | pwa-state | Provides `cell.health` WebSocket events (R2) |
| pwa-scaffold | pwa-state | API client consumed by WebSocket hook for REST fetches |
| pwa-scaffold | pwa-screens | API client called from all screens |
| pwa-scaffold | pwa-tests | API client module under test (R3) |
| pwa-state | pwa-screens | `AppState` and `dispatch` consumed by all screens |
| pwa-state | pwa-tests | Reducer (R2) and WebSocket hook (R3) under test |

## Dependency Graph

```
server-gaps ──────────────────────────────────────────────┐
                                                           ▼
pwa-scaffold ──────────────────────────────────────────► pwa-screens
     │                                                     ▲
     ▼                                                     │
pwa-state ────────────────────────────────────────────────┘
     │
     ▼
pwa-tests (depends on pwa-scaffold + pwa-state)
```

### Implementation Order

1. **server-gaps** — no dependencies; implement first (independent of all PWA work)
2. **pwa-scaffold** — no dependencies on other domains; implement in parallel with server-gaps
3. **pwa-state** — depends on pwa-scaffold (API client interface must be settled)
4. **pwa-screens** — depends on pwa-state + pwa-scaffold
5. **pwa-tests** — depends on pwa-state + pwa-scaffold (can start alongside pwa-screens)

## Changelog
