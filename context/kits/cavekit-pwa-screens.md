---
created: "2026-04-19T00:00:00Z"
last_edited: "2026-04-19T00:00:00Z"
complexity: medium
---

# Cavekit: PWA Screens

## Scope

All eight user-visible screens of the HomeView PWA, the navigation between them, and the visual design contract each screen must satisfy. This domain owns the rendering and interaction layer only -- it reads from `AppState` (provided by pwa-state) and dispatches actions. It calls API methods (provided by pwa-scaffold) but owns no networking or state management logic itself.

## Requirements

### R1: Pair Screen

**Description:** The entry screen shown when the app has no stored server connection (`pairPhase === "unpaired"`). Collects a server URL and 6-digit pairing code from the user.

**Acceptance Criteria:**
- [ ] Screen is rendered when `pairPhase` equals `"unpaired"` and is the only screen accessible in that state
- [ ] Contains a text input for the server URL
- [ ] Contains a numeric-only input for the 6-digit pairing code
- [ ] Code input rejects non-numeric characters and enforces exactly 6 digits before enabling submit
- [ ] Submit is disabled until both fields are non-empty and the code field contains exactly 6 digits
- [ ] On submit, calls `POST /api/v1/pair` with `{"code": "<value>"}` against the entered server URL
- [ ] On success, stores the returned token, dispatches `SET_SERVER` with the server URL and token, and navigates to the Main screen
- [ ] On error, displays an inline error message below the code field; error text uses `--color-error` (DESIGN.md Section 2)
- [ ] Input styling follows DESIGN.md Section 4.5 (Text Inputs)
- [ ] Button styling follows DESIGN.md Section 4.1 (Primary button)
- [ ] Pairing code input uses `--font-mono` (DESIGN.md Section 3)
- [ ] All interactive elements meet the 44px minimum touch target (DESIGN.md Section 7)

**Dependencies:** cavekit-pwa-scaffold (API client), cavekit-pwa-state (`SET_SERVER` action, `pairPhase` state)

### R2: Main / Status Screen

**Description:** The primary screen shown when the app is paired (`pairPhase === "paired"`). Displays the current layout as a grid of CellCards and provides navigation to all other paired-state screens.

**Acceptance Criteria:**
- [ ] Screen is rendered when `pairPhase` equals `"paired"` and is the default landing screen in that state
- [ ] Renders one CellCard per cell in `AppState.status.cells`, arranged in a proportional grid matching the active layout geometry
- [ ] Each CellCard displays the source name when a source is assigned, or an empty-state indicator when unassigned
- [ ] Each CellCard displays the cell status as one of: EMPTY, STARTING, RUNNING, ERROR
- [ ] Each CellCard displays an audio-active indicator when the cell index matches `AppState.status.audio.active_cell`
- [ ] CellCard visual states follow DESIGN.md Section 4.2 (CellCard): empty uses dashed border, running shows `--color-success` left accent bar, error shows `--color-error` left accent bar, audio-active shows speaker badge with `--color-accent`
- [ ] Tapping a CellCard opens the Source Picker (R3)
- [ ] Navigation elements are present for: Layouts (R4), Audio (R5), Presets (R6), Settings (R8)
- [ ] When `wsConnected` is `false`, a connection status banner is visible using `--color-warning` (DESIGN.md Section 2) and `--color-warning-muted` background
- [ ] When `wsConnected` is `true`, the connection status banner is not visible
- [ ] Cell list layout follows DESIGN.md Section 5 grid patterns: single column on mobile, two columns at tablet breakpoint (768px), auto-fill at desktop breakpoint (1024px)

**Dependencies:** cavekit-pwa-state (`AppState.status`, `wsConnected`), cavekit-pwa-scaffold (API client)

### R3: Source Picker

**Description:** A modal overlay opened from a CellCard tap on the Main screen. Lists all available sources for assignment to the selected cell.

**Acceptance Criteria:**
- [ ] Opens as a bottom sheet on viewports below 768px and as a centered modal at 768px and above, per DESIGN.md Section 4.3 (SourcePickerModal)
- [ ] Fetches sources from the API if not yet cached in `AppState`; displays a loading indicator while the fetch is in progress
- [ ] Displays each source with its name and icon
- [ ] Tapping a source calls `PUT /api/v1/cells/{cell_index}/source` with `{"source_id": "<id>"}`
- [ ] On successful source assignment, the modal closes; the Main screen cell state updates via WebSocket push
- [ ] Contains a "Clear" action that calls `DELETE /api/v1/cells/{cell_index}/source`
- [ ] On successful clear, the modal closes; the Main screen cell state updates via WebSocket push
- [ ] On API error, an inline error message is displayed within the modal using `--color-error` (DESIGN.md Section 2)
- [ ] Backdrop uses `--shadow-high` elevation and backdrop blur per DESIGN.md Section 6
- [ ] Sheet background uses `--color-bg-elevated` (DESIGN.md Section 2)
- [ ] All interactive elements meet the 44px minimum touch target (DESIGN.md Section 7)

**Dependencies:** cavekit-pwa-state (`AppState.sources`, `AppState.status.cells`), cavekit-pwa-scaffold (API client)

### R4: Layout Picker Screen

**Description:** Displays all available layouts and allows the user to switch the active layout.

**Acceptance Criteria:**
- [ ] Navigable from the Main screen navigation controls
- [ ] Displays all layouts from `AppState.layouts`; fetches from the API if `AppState.layouts` is null
- [ ] Each layout entry shows its name and a proportional cell preview grid (miniature representation of cell positions)
- [ ] The currently active layout is visually distinguished using `--color-accent-muted` background and `--color-accent` border (DESIGN.md Section 4.4, `aria-selected="true"` state)
- [ ] Tapping a non-active layout calls `PUT /api/v1/layout` with `{"layout_id": "<id>"}`
- [ ] On success, navigates back to the Main screen; layout state updates via WebSocket push
- [ ] On API error, an inline error message is displayed using `--color-error` (DESIGN.md Section 2)
- [ ] Layout card preview has a 16:9 aspect ratio per DESIGN.md Section 4.4
- [ ] Layout card grid is responsive: 2 columns on mobile, 3 columns at tablet, auto-fill at desktop per DESIGN.md Section 8 behavior matrix

**Dependencies:** cavekit-pwa-state (`AppState.layouts`, `AppState.status.layout_id`), cavekit-pwa-scaffold (API client)

### R5: Audio Picker Screen

**Description:** Displays current cells and allows the user to select which cell provides audio output.

**Acceptance Criteria:**
- [ ] Navigable from the Main screen navigation controls
- [ ] Lists all cells from `AppState.status.cells`
- [ ] The cell currently providing audio (`AppState.status.audio.active_cell`) is highlighted using `--color-accent` (DESIGN.md Section 2)
- [ ] Only cells with status RUNNING are tappable; cells with any other status are rendered in a disabled state per DESIGN.md Section 4.1 (button disabled: `--color-bg-overlay` background, `--color-text-muted` text, `cursor: not-allowed`)
- [ ] Tapping a RUNNING cell calls `PUT /api/v1/audio/active` with `{"cell_index": <int>}`
- [ ] On success, the audio active indicator updates; state updates via WebSocket push
- [ ] On API error, an inline error message is displayed using `--color-error` (DESIGN.md Section 2)

**Dependencies:** cavekit-pwa-state (`AppState.status.cells`, `AppState.status.audio`), cavekit-pwa-scaffold (API client)

### R6: Presets Screen

**Description:** Full CRUD interface for managing presets (saved layout + cell assignment + audio configurations).

**Acceptance Criteria:**
- [ ] Navigable from the Main screen navigation controls
- [ ] Lists all presets from `AppState.presets`; fetches from the API if `AppState.presets` is null
- [ ] Each preset row displays the preset name
- [ ] Each preset row contains an "Apply" action and a "Delete" action
- [ ] "Apply" calls `PUT /api/v1/presets/{id}/apply`; state updates via WebSocket push
- [ ] "Delete" calls `DELETE /api/v1/presets/{id}`; the preset is removed from the displayed list on success
- [ ] A "Save current" action is available that prompts the user for a preset name
- [ ] "Save current" calls `POST /api/v1/presets` with a body containing `name` and `cell_assignments` as `Record<string, string | null>` keyed by cell index string; refreshes the preset list on success
- [ ] On any API error, an inline error message is displayed using `--color-error` (DESIGN.md Section 2)
- [ ] "Delete" action uses destructive button styling per DESIGN.md Section 4.1 (Destructive variant)
- [ ] "Apply" action uses primary button styling per DESIGN.md Section 4.1 (Primary variant)
- [ ] All interactive elements meet the 44px minimum touch target (DESIGN.md Section 7)

**Dependencies:** cavekit-pwa-state (`AppState.presets`, `AppState.status`), cavekit-pwa-scaffold (API client)

### R7: Interactive Mode

**Description:** Per-cell interactive mode toggle, allowing the user to enter a full-interaction state with a single cell's content.

**Acceptance Criteria:**
- [ ] A "Start Interactive" action is available for cells with status RUNNING, accessible from the Main screen
- [ ] "Start Interactive" calls `POST /api/v1/interactive/start` with `{"cell_index": <int>}`
- [ ] On success, dispatches `SET_INTERACTIVE` with the cell index; the UI indicates which cell is in interactive mode
- [ ] On 409 response, displays an "Interactive mode already active" message using `--color-warning` (DESIGN.md Section 2)
- [ ] A "Stop Interactive" action is available when `AppState.interactiveCell` is not null
- [ ] "Stop Interactive" calls `POST /api/v1/interactive/stop` (no body)
- [ ] On success, dispatches `CLEAR_INTERACTIVE`; the interactive indicator is removed
- [ ] `interactiveCell` resets to null on WebSocket reconnect (local-only state, not persisted)

**Dependencies:** cavekit-pwa-state (`AppState.interactiveCell`, `SET_INTERACTIVE`, `CLEAR_INTERACTIVE` actions), cavekit-pwa-scaffold (API client)

### R8: Settings Screen

**Description:** Minimal settings screen for managing the server connection.

**Acceptance Criteria:**
- [ ] Navigable from the Main screen navigation controls
- [ ] Contains a "Forget server" action
- [ ] "Forget server" clears the stored server URL and token from persistent local storage
- [ ] "Forget server" dispatches `CLEAR_SERVER`, which resets `pairPhase` to `"unpaired"`
- [ ] After "Forget server", the app navigates to the Pair screen (R1)
- [ ] "Forget server" button uses destructive button styling per DESIGN.md Section 4.1 (Destructive variant)
- [ ] The button meets the 44px minimum touch target (DESIGN.md Section 7)

**Dependencies:** cavekit-pwa-state (`CLEAR_SERVER` action, `pairPhase`)

## Out of Scope

- State management logic, reducer, and WebSocket hook (see cavekit-pwa-state)
- API client implementation and HTTP/fetch wrappers (see cavekit-pwa-scaffold)
- Source CRUD -- sources are server-managed in v1; the PWA only reads them
- Multi-server support (connecting to more than one HomeView server)
- Push notifications
- Dark/light theme toggle UI -- DESIGN.md defines tokens for both modes, but the toggle switch is deferred
- Offline mode or service worker caching strategies
- Animations and transition choreography beyond what DESIGN.md specifies in component CSS

## Cross-References

- See also: cavekit-pwa-state.md (provides `AppState`, dispatch actions, `wsConnected`, `pairPhase`, `interactiveCell`)
- See also: cavekit-pwa-scaffold.md (provides typed API client and Vite project scaffold)
- See also: cavekit-server-gaps.md (R1 pairing error envelope consumed by R1 Pair Screen; R2 cell.health events consumed by R2 Main Screen; R4 static serving enables production deployment)
- See also: DESIGN.md (visual design system -- all token and component references above)

## Changelog
