"""Tests for interactive mode start/stop per cell."""

import pytest
from httpx import AsyncClient, ASGITransport

from server.db import init_db
from server.auth.pairing import PairingManager


@pytest.fixture
async def db_path(tmp_path) -> str:
    path = str(tmp_path / "test.db")
    await init_db(path)
    return path


@pytest.fixture
async def auth_token(db_path) -> str:
    mgr = PairingManager(db_path)
    code = await mgr.generate_pairing_code()
    token = await mgr.validate_code(code)
    return token


@pytest.fixture
async def api_client(db_path, auth_token):
    from server.main import create_app

    app = create_app(db_path=db_path, mock_mode=True)
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=True),
        base_url="http://test",
        headers={"Authorization": f"Bearer {auth_token}"},
    ) as ac:
        async with app.router.lifespan_context(app):
            yield ac


class TestInteractiveManager:
    def _make_manager(self):
        from server.composition.interactive import InteractiveManager

        return InteractiveManager()

    def test_initial_state_not_active(self):
        """Interactive mode is not active at start."""
        mgr = self._make_manager()
        assert mgr.is_active() is False
        assert mgr.active_cell_index is None

    def test_start_sets_active(self):
        """start() marks the given cell as interactive."""
        mgr = self._make_manager()
        mgr.start(cell_index=0)
        assert mgr.is_active() is True
        assert mgr.active_cell_index == 0

    def test_stop_clears_active(self):
        """stop() clears the interactive state."""
        mgr = self._make_manager()
        mgr.start(cell_index=1)
        mgr.stop()
        assert mgr.is_active() is False
        assert mgr.active_cell_index is None

    def test_start_same_cell_is_idempotent(self):
        """start() on the already-active cell is a no-op."""
        mgr = self._make_manager()
        mgr.start(cell_index=2)
        mgr.start(cell_index=2)  # should not raise
        assert mgr.active_cell_index == 2

    def test_start_different_cell_raises(self):
        """start() on a different cell when already active raises ConflictError."""
        from server.composition.interactive import InteractiveConflictError

        mgr = self._make_manager()
        mgr.start(cell_index=0)
        with pytest.raises(InteractiveConflictError):
            mgr.start(cell_index=1)


class TestInteractiveAPI:
    @pytest.mark.asyncio
    async def test_start_interactive(self, api_client):
        """POST /api/v1/interactive/start sets interactive mode."""
        r = await api_client.post("/api/v1/interactive/start", json={"cell_index": 0})
        assert r.status_code == 200
        data = r.json()
        assert data["active_cell_index"] == 0
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_stop_interactive(self, api_client):
        """POST /api/v1/interactive/stop clears interactive mode."""
        await api_client.post("/api/v1/interactive/start", json={"cell_index": 0})
        r = await api_client.post("/api/v1/interactive/stop")
        assert r.status_code == 200
        data = r.json()
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_start_conflict_returns_409(self, api_client):
        """Starting interactive on a different cell when active returns 409."""
        await api_client.post("/api/v1/interactive/start", json={"cell_index": 0})
        r = await api_client.post("/api/v1/interactive/start", json={"cell_index": 1})
        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_start_missing_cell_index_returns_422(self, api_client):
        """POST /api/v1/interactive/start without cell_index returns 422."""
        r = await api_client.post("/api/v1/interactive/start", json={})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_stop_when_not_active_is_ok(self, api_client):
        """POST /api/v1/interactive/stop when not active returns 200."""
        r = await api_client.post("/api/v1/interactive/stop")
        assert r.status_code == 200
        assert r.json()["is_active"] is False
