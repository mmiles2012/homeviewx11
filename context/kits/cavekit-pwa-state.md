---
created: "2026-04-19T00:00:00Z"
last_edited: "2026-04-19T00:00:00Z"
complexity: medium
---

# Cavekit: PWA State

## Scope

Client-side state management for the HomeView PWA. Covers the canonical app state shape, a pure reducer for state transitions, a WebSocket hook for real-time server synchronization, and a context provider that wires everything together. This is the live data layer between the server and the UI.

## Requirements

### R1: App State Shape

**Description:** A single `AppState` type must represent all data the UI needs. Downstream screens read from this type exclusively — no secondary stores or ad-hoc fetch caches.

**Acceptance Criteria:**
- [ ] `AppState` contains a `serverUrl` field typed as `string | null`
- [ ] `AppState` contains a `token` field typed as `string | null`
- [ ] `AppState` contains a `status` field typed as `ServerStatus | null`
- [ ] `AppState` contains a `sources` field typed as `Source[] | null`
- [ ] `AppState` contains a `layouts` field typed as `Layout[] | null`
- [ ] `AppState` contains a `presets` field typed as `Preset[] | null`
- [ ] `AppState` contains a `wsConnected` field typed as `boolean`
- [ ] `AppState` contains an `interactiveCell` field typed as `number | null`
- [ ] `AppState` contains a `pairPhase` field typed as `"unpaired" | "pairing" | "paired"`
- [ ] `ServerStatus` has the shape `{ layout_id: string, cells: CellStatus[], audio: { active_cell: number | null } }`
- [ ] `CellStatus` has the shape `{ index: number, source_id: string | null, status: string, pid: number | null }`
- [ ] `Source` has the shape `{ id: string, name: string, type: string, url: string, icon_url: string | null, requires_widevine: boolean, notes: string | null }`
- [ ] `Preset` has the shape `{ id: string, name: string, layout_id: string, cell_assignments: Record<string, string | null>, active_audio_cell: number | null }`
- [ ] `Layout` has the shape `{ id: string, name: string, gap_px: number, cells: Array<{ index: number, role: string, x: number, y: number, w: number, h: number }> }`
- [ ] The initial state has `serverUrl: null`, `token: null`, `status: null`, `sources: null`, `layouts: null`, `presets: null`, `wsConnected: false`, `interactiveCell: null`, `pairPhase: "unpaired"`

**Dependencies:** None

### R2: Reducer

**Description:** A pure reducer function handles all state transitions via typed action objects. It produces a new state for every dispatch — no mutations, no side effects.

**Acceptance Criteria:**
- [ ] The reducer accepts `(state: AppState, action: Action)` and returns `AppState`
- [ ] Action type `SET_SERVER` with payload `{ serverUrl: string, token: string }` sets `serverUrl`, `token`, and `pairPhase` to `"paired"`
- [ ] Action type `CLEAR_SERVER` resets all fields to their initial values (as defined in R1)
- [ ] Action type `SET_STATUS` with payload `ServerStatus` replaces the `status` field
- [ ] Action type `SET_SOURCES` with payload `Source[]` replaces the `sources` field
- [ ] Action type `SET_LAYOUTS` with payload `Layout[]` replaces the `layouts` field
- [ ] Action type `SET_PRESETS` with payload `Preset[]` replaces the `presets` field
- [ ] Action type `SET_WS_CONNECTED` with payload `boolean` sets the `wsConnected` field
- [ ] Action type `SET_INTERACTIVE` with payload `number` sets the `interactiveCell` field
- [ ] Action type `CLEAR_INTERACTIVE` sets `interactiveCell` to `null`
- [ ] The reducer returns a new object for every action (never mutates the input state)
- [ ] The reducer returns the input state unchanged for unrecognized action types
- [ ] The `Action` type is a discriminated union of all action types listed above

**Dependencies:** R1

### R3: WebSocket Hook

**Description:** A hook manages the WebSocket connection lifecycle, dispatching state updates as server events arrive and reconnecting with exponential backoff on disconnection.

**Acceptance Criteria:**
- [ ] The hook connects to `ws://{serverUrl}/ws/control?token={token}` when both `serverUrl` and `token` are non-null
- [ ] The hook does not attempt connection when `token` is null
- [ ] On receiving a message with `type: "state.updated"`, the hook dispatches `SET_STATUS` with the message's `data` field
- [ ] On receiving a message with `type: "cell.health"`, the hook dispatches `SET_STATUS` by fetching `GET /api/v1/status` and using the response
- [ ] On successful connection open, the hook fetches `GET /api/v1/status` and dispatches `SET_STATUS` with the response
- [ ] On successful connection open, the hook dispatches `SET_WS_CONNECTED` with `true`
- [ ] On connection close, the hook dispatches `SET_WS_CONNECTED` with `false`
- [ ] On connection error, the hook dispatches `SET_WS_CONNECTED` with `false`
- [ ] After disconnection, the hook reconnects with exponential backoff: initial delay 1 second, multiplier 2, maximum delay 30 seconds
- [ ] Backoff delay resets to the initial value on successful reconnection
- [ ] On unmount, the hook closes the WebSocket connection and cancels any pending reconnect timer
- [ ] When `token` transitions from non-null to null, the hook closes the WebSocket connection and cancels any pending reconnect timer

**Dependencies:** R1, R2; cavekit-pwa-scaffold.md (API client for `GET /api/v1/status`); cavekit-server-gaps.md R2 (cell.health events)

### R4: Context Provider

**Description:** A context provider makes state and dispatch available to the entire component tree. It handles persistence of pairing credentials and wires the WebSocket hook.

**Acceptance Criteria:**
- [ ] The provider exposes `state` (of type `AppState`) and `dispatch` (dispatch function) to all descendant components
- [ ] On mount, the provider reads `serverUrl` and `token` from `localStorage` and initializes state accordingly: if both are present, `pairPhase` is `"paired"`; otherwise `pairPhase` is `"unpaired"`
- [ ] When a `SET_SERVER` action is dispatched, the provider persists `serverUrl` and `token` to `localStorage`
- [ ] When a `CLEAR_SERVER` action is dispatched, the provider removes `serverUrl` and `token` from `localStorage`
- [ ] The provider activates the WebSocket hook (R3) using the current `serverUrl` and `token` from state
- [ ] Consuming components that do not use `state` or `dispatch` are not forced to re-render on state changes (the provider does not cause unnecessary re-renders beyond what the context mechanism provides)
- [ ] Accessing the context outside of the provider throws or returns a clear error

**Dependencies:** R1, R2, R3

## Out of Scope

- UI rendering of any kind (screens, components, styling)
- API client implementation (HTTP fetch wrappers) — see cavekit-pwa-scaffold.md
- Unit or integration tests for this domain — see cavekit-pwa-tests.md
- Multi-server support (v2)
- Offline/service-worker caching of state

## Cross-References

- See also: `cavekit-pwa-scaffold.md` (provides the API client consumed by the WebSocket hook for REST fetches)
- See also: `cavekit-pwa-screens.md` (consumes `state` and `dispatch` from the context provider)
- See also: `cavekit-pwa-tests.md` (tests the reducer and WebSocket hook defined in this domain)
- See also: `cavekit-server-gaps.md` R2 (provides `cell.health` WebSocket events consumed by the hook)

## Changelog
