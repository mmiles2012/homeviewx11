---
paths:
  - "tests/**"
  - "server/**"
---

# Testing — HomeView specifics

## Fixtures live in `tests/conftest.py`

The `client` fixture is an `httpx.AsyncClient` bound to the FastAPI `app` via
`ASGITransport`. It is async — tests that use it must be `async def` (pytest-asyncio
is in `auto` mode, no decorator needed).

```python
async def test_something(client):
    response = await client.get("/api/v1/server/health")
    assert response.status_code == 200
```

## Mock mode is mandatory for tests

The entire test suite runs with `HOMEVIEW_MOCK=1` behavior (set via config defaults
in the mock app factory). Consequences:

- `ChromiumLauncher` is `MockChromiumLauncher` — it returns fake PIDs, does not
  spawn subprocesses. Do not assert on real process state.
- `WindowManager` is `MockWindowManager` — no X11 calls, no-op geometry application.
- `AudioRouter` does not touch PulseAudio.
- Display resolution is 1920×1080 by default.

When adding a new composition-layer feature, ensure the mock path also exercises it.
If a test requires a real subprocess or X11 connection, it is the wrong test — redesign
against the mock abstractions.

## Test naming

`test_<function>_<scenario>_<expected>`. Match the module-to-test 1:1 mapping: a new
module in `server/composition/foo.py` needs `tests/test_foo.py`.

## Running

```bash
uv run pytest -q                                    # full suite
uv run pytest -q --cov=server --cov-fail-under=80  # with coverage (80% minimum)
uv run pytest tests/test_engine.py -q              # single file
uv run pytest tests/test_engine.py::test_name -q   # single test
```

## Mocking external dependencies in unit tests

Mock at the call site (where imported), not where defined. Anything that would touch
the OS in production must be mocked:

| Dependency | Where to mock |
|------------|---------------|
| Chromium subprocess | Already handled via `MockChromiumLauncher` injection |
| X11 (`python-xlib`) | Already handled via `MockWindowManager` injection |
| PulseAudio | Patch `server.audio.router` module-level helpers |
| aiosqlite | Use temp DB path via fixture — do not mock the driver |
| HTTP out (`httpx`) | `@patch` the client at the module that imports it |

## After tests pass, still run the server

Unit tests with mocks prove the logic works. For API behavior, also run:

```bash
HOMEVIEW_MOCK=1 uv run homeview
# then hit endpoints with curl or httpx to verify the full stack
```

Especially before marking work complete on changes that touch routing, auth, or
WebSocket broadcasting — these have integration points that mocks don't exercise.
