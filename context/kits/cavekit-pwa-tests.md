---
created: "2026-04-19T00:00:00Z"
last_edited: "2026-04-19T00:00:00Z"
complexity: medium
---

# Cavekit: PWA Tests

## Scope

Vitest unit tests for the PWA's state layer and API client. Covers test infrastructure setup, test suites for the reducer, API client, and WebSocket hook, and enforced coverage thresholds. This domain defines WHAT must be tested and validated -- not the implementations under test.

## Requirements

### R1: Test Infrastructure

**Description:** The PWA must have a working test runner, environment, and global mock surface sufficient to test state management and network interactions without real servers or browsers.

**Acceptance Criteria:**
- [ ] Vitest is configured with `jsdom` as the test environment
- [ ] `pwa/package.json` contains a `"test"` script that runs Vitest
- [ ] `pwa/package.json` contains a `"test:coverage"` script that runs Vitest with coverage enabled
- [ ] A `vitest.config.ts` (or equivalent Vitest configuration) exists in `pwa/` and defines coverage thresholds for `src/state/` and `src/api/` directories
- [ ] `fetch` is mockable at the global level within tests (tests can intercept and stub `fetch` calls)
- [ ] `WebSocket` is mockable at the global level within tests (tests can intercept and stub `WebSocket` construction and events)

**Dependencies:** None

### R2: Reducer Tests

**Description:** Every action type accepted by the state reducer must have at least one test verifying correct state transformation.

**Acceptance Criteria:**
- [ ] A test asserts that dispatching `SET_SERVER` stores `serverUrl` and `token` in state and sets `pairPhase` to `"paired"`
- [ ] A test asserts that dispatching `CLEAR_SERVER` resets all state fields to their initial values
- [ ] A test asserts that dispatching `SET_STATUS` replaces the status object in state without wiping unrelated fields
- [ ] A test asserts that dispatching `SET_SOURCES` stores the provided source list in state
- [ ] A test asserts that dispatching `SET_LAYOUTS` stores the provided layout list in state
- [ ] A test asserts that dispatching `SET_PRESETS` stores the provided preset list in state
- [ ] A test asserts that dispatching `SET_WS_CONNECTED` with `true` sets `wsConnected` to `true`, and with `false` sets it to `false`
- [ ] A test asserts that dispatching `SET_INTERACTIVE` sets `interactiveCell` to the provided value
- [ ] A test asserts that dispatching `CLEAR_INTERACTIVE` sets `interactiveCell` to `null` (or equivalent absent value)

**Dependencies:** cavekit-pwa-state R1 (reducer implementation)

### R3: API Client Tests

**Description:** Key API client functions must be tested against mocked `fetch` to verify correct HTTP method, URL construction, request body, authorization headers, and error handling.

**Acceptance Criteria:**
- [ ] A test for `pair(code)` asserts: POST method, URL ends with `/api/v1/pair`, request body contains the pairing code, and a successful (200) response returns the token
- [ ] A test for `assignSource(cellIndex, sourceId)` asserts: PUT method, URL contains the cell index as a path parameter, request body contains the source ID, and the `Authorization` header is present with a Bearer token
- [ ] A test for `getPresets()` asserts: GET method, URL ends with `/api/v1/presets`, `Authorization` header is present, and the response is parsed into a preset array
- [ ] A test for error handling asserts: when the server returns a non-2xx response with a `{"error": {"code": "...", ...}}` body, the client throws an error that includes the parsed error code

**Dependencies:** cavekit-pwa-scaffold R4 (API client implementation)

### R4: WebSocket Hook Tests

**Description:** The WebSocket connection hook must be tested for reconnection behavior and state dispatch using a mocked `WebSocket`.

**Acceptance Criteria:**
- [ ] A test asserts that when a WebSocket connection closes, a reconnect attempt fires after a delay
- [ ] A test asserts that on successful reconnection, `SET_WS_CONNECTED` is dispatched with `true`
- [ ] A test asserts that when the auth token is `null`, no WebSocket connection attempt is made
- [ ] A test asserts exponential backoff: the delay before the second reconnect attempt is greater than the delay before the first

**Dependencies:** cavekit-pwa-state R3 (WebSocket hook implementation)

### R5: Coverage Threshold

**Description:** Automated coverage checks must enforce minimum line coverage for state and API modules.

**Acceptance Criteria:**
- [ ] Running `npm run test:coverage` in `pwa/` enforces a minimum of 80% line coverage for files in `src/state/`
- [ ] Running `npm run test:coverage` in `pwa/` enforces a minimum of 80% line coverage for files in `src/api/`
- [ ] `npm run test:coverage` exits with a non-zero code if either threshold is not met

**Dependencies:** R1 (test infrastructure must be configured with thresholds)

## Out of Scope

- UI component tests (no rendering or DOM interaction tests for React components)
- End-to-end or integration tests against a running HomeView server
- Server-side Python tests (covered by pytest in `tests/`)
- Performance or load testing
- Visual regression testing

## Cross-References

- See also: `cavekit-pwa-state.md` (defines the reducer and WebSocket hook that R2 and R4 test)
- See also: `cavekit-pwa-scaffold.md` (defines the API client that R3 tests)

## Changelog
