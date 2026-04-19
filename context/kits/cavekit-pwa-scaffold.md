---
created: "2026-04-19T00:00:00Z"
last_edited: "2026-04-19T00:00:00Z"
complexity: medium
---

# Cavekit: PWA Scaffold

## Scope

PWA project scaffolding, development tooling, API client layer, and production build integration. This domain covers everything needed to stand up the PWA project within the HomeView repository and connect it to the existing server — but NOT state management, NOT UI screens, and NOT test setup.

## Requirements

### R1: Project Scaffold

**Description:** A `pwa/` directory at the repository root contains a buildable Vite + React + TypeScript project with the minimum entry-point files needed for a single-page application.

**Acceptance Criteria:**

- [ ] `pwa/package.json` exists and declares `react`, `react-dom`, and `typescript` as dependencies
- [ ] `pwa/tsconfig.json` exists and enables strict mode
- [ ] `pwa/vite.config.ts` exists
- [ ] `pwa/index.html` exists and contains a root mount element
- [ ] `pwa/src/main.tsx` exists and renders the root React component into the mount element
- [ ] `pwa/src/App.tsx` exists and exports a default React component
- [ ] Running `npm run build` inside `pwa/` exits with code 0 and produces output files

**Dependencies:** None

### R2: PWA Manifest and Service Worker

**Description:** The application is installable as a Progressive Web App. A web app manifest declares the application identity and display preferences. A service worker provides offline caching of static assets while ensuring API requests always go to the network.

**Acceptance Criteria:**

- [ ] A web app manifest is served with `name` set to `"HomeView"` and `short_name` set to `"HomeView"`
- [ ] The manifest `display` field is `"standalone"`
- [ ] The manifest `theme_color` is `#0A0A0F` (matching `--color-bg-deep` from DESIGN.md Section 2, dark mode)
- [ ] The manifest `background_color` is `#0A0A0F`
- [ ] The manifest declares icons at 192x192 and 512x512 pixel sizes
- [ ] A service worker is registered on page load
- [ ] The service worker caches static assets (JS, CSS, HTML, images) for offline availability
- [ ] All requests matching `/api/*` use a network-first strategy and are never served from cache when the network is available
- [ ] All requests matching `/ws/*` are not intercepted by the service worker
- [ ] Running Lighthouse PWA audit against a production build yields a score of 90 or higher

**Dependencies:** R1 (Project Scaffold)

### R3: Vite Dev Proxy

**Description:** The Vite development server proxies API and WebSocket requests to the local HomeView server, eliminating CORS issues during development.

**Acceptance Criteria:**

- [ ] HTTP requests to `/api` on the Vite dev server are forwarded to `http://localhost:8000`
- [ ] WebSocket connections to `/ws` on the Vite dev server are forwarded to `ws://localhost:8000`
- [ ] The proxy preserves WebSocket upgrade headers so that `/ws/control` connections succeed
- [ ] The proxy preserves request headers including `Authorization`

**Dependencies:** R1 (Project Scaffold)

### R4: API Client Layer

**Description:** A typed API client module wraps all server REST endpoints. The client attaches authentication headers, parses typed errors from the server's error envelope, and persists the bearer token across sessions.

**Acceptance Criteria:**

- [ ] An API client module exists under `pwa/src/` and exports typed functions for every endpoint listed below
- [ ] `getPairCode()` calls `GET /api/v1/pair/code` and returns an object with `code` and `expires_at` fields, or throws on 404
- [ ] `pair(code)` calls `POST /api/v1/pair` with body `{code}` and returns the bearer token string, or throws on 4xx
- [ ] `getStatus()` calls `GET /api/v1/status` and returns the full status shape (layout_id, cells array, audio object)
- [ ] `getSources()` calls `GET /api/v1/sources` and returns the source list
- [ ] `assignSource(cellIndex, sourceId)` calls `PUT /api/v1/cells/{cellIndex}/source` with body `{source_id}`
- [ ] `clearCell(cellIndex)` calls `DELETE /api/v1/cells/{cellIndex}/source`
- [ ] `setLayout(layoutId)` calls `PUT /api/v1/layout` with body `{layout_id}`
- [ ] `getLayouts()` calls `GET /api/v1/layouts` and returns the layout list
- [ ] `setActiveAudio(cellIndex)` calls `PUT /api/v1/audio/active` with body `{cell_index}`
- [ ] `getPresets()` calls `GET /api/v1/presets` and returns the preset list
- [ ] `savePreset(name)` calls `POST /api/v1/presets` with body `{name}` and returns the created preset
- [ ] `applyPreset(presetId)` calls `PUT /api/v1/presets/{presetId}/apply`
- [ ] `deletePreset(presetId)` calls `DELETE /api/v1/presets/{presetId}`
- [ ] `startInteractive(cellIndex)` calls `POST /api/v1/interactive/start` with body `{cell_index}`
- [ ] `stopInteractive()` calls `POST /api/v1/interactive/stop`
- [ ] Every function that calls a protected endpoint attaches an `Authorization: Bearer <token>` header when a token is available
- [ ] On non-2xx responses, the client parses the server error envelope (`{"error": {"code": ..., "message": ...}}`) and throws a typed error containing both `code` and `message`
- [ ] The `getPairCode()` and `pair()` functions do not attach an `Authorization` header (these are public endpoints)
- [ ] The API client accepts the bearer token as a parameter or reads it from the context layer — it does not persist or load from `localStorage` directly (persistence is owned by cavekit-pwa-state R4)

**Dependencies:** R1 (Project Scaffold)

### R5: Production Build Integration

**Description:** The PWA production build outputs directly into the server's static file directory so the server can serve the built PWA without a separate web server.

**Acceptance Criteria:**

- [ ] The Vite build output directory is configured to write to `server/static/` relative to the repository root
- [ ] The build clears the output directory before writing (empty-out-dir behavior)
- [ ] After running `npm run build` in `pwa/`, the file `server/static/index.html` exists
- [ ] The `server/static/` directory is listed in the repository's `.gitignore`

**Dependencies:** R1 (Project Scaffold)

## Out of Scope

- State management and WebSocket event hooks (see cavekit-pwa-state)
- UI screens, components, and visual design implementation (see cavekit-pwa-screens)
- Vitest test configuration and test files (see cavekit-pwa-tests)
- Server-side changes such as CORS configuration and static file serving (see cavekit-server-gaps)
- Source CRUD endpoints (`POST /api/v1/sources`, `PUT /api/v1/sources/{id}`, `DELETE /api/v1/sources/{id}`) in the API client — these are admin operations not needed by the PWA remote
- Icon asset creation (192x192 and 512x512 PNGs must exist but their visual content is not specified here)

## Cross-References

- See also: cavekit-server-gaps.md (provides CORS headers and static file serving so the built PWA can be served by the HomeView server)
- See also: cavekit-pwa-state.md (builds on this scaffold to add reactive state management and WebSocket integration)
- See also: cavekit-pwa-screens.md (builds on this scaffold to add UI screens and components)
- See also: cavekit-pwa-tests.md (tests the API client and other modules from this domain)
- See also: DESIGN.md Section 2 (color palette — referenced by R2 for manifest theme values)

## Changelog
