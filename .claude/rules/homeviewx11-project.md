# HomeView — Project Rules

**Last Updated:** 2026-04-13

Canonical project instructions live in `CLAUDE.md` at the repo root. Read that file for:
stack, running the server, testing, code conventions, architecture, layout JSON schema,
key files, and the quality checklist.

@../../CLAUDE.md

## Additional tribal knowledge

- **Python 3.12+ only.** `pyproject.toml` pins `requires-python = ">=3.12"` — do not
  use `Union[X, Y]` / `Optional[X]` / `List[X]`; use `X | Y` / `X | None` / `list[X]`.
- **`from __future__ import annotations`** is required at the top of every module in
  `server/` — this is already enforced by the existing codebase, match it in new files.
- **Test map:** `tests/test_<module>.py` → `server/<subpkg>/<module>.py` is 1:1. When
  adding a new module in `server/`, add `tests/test_<same_name>.py`.
- **Never set `HOMEVIEW_MOCK=0` in tests.** The test suite runs entirely in mock mode;
  the fixtures in `tests/conftest.py` assume no real X11 / Chromium / PulseAudio.
- **Error envelope shape is non-negotiable:** all error responses must be
  `{"error": {"code": "SNAKE_CASE", "message": "...", "details": {}}}`. Do not return
  bare FastAPI `HTTPException` detail strings — wrap them.
- **REST prefix:** every REST route lives under `/api/v1/`. WebSocket is at
  `/ws/control` (no `/api/v1` prefix).
- **`ruff format` and `ruff check` are both required** before marking work done — see
  the checklist in `CLAUDE.md`.
