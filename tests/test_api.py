"""Tests for FastAPI REST endpoints."""

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
        # Trigger FastAPI lifespan (runs init_db + engine.start)
        async with app.router.lifespan_context(app):
            yield ac


class TestHealthAndInfo:
    @pytest.mark.asyncio
    async def test_health_no_auth(self, db_path):
        """GET /api/v1/server/health requires no auth."""
        from server.main import create_app

        app = create_app(db_path=db_path, mock_mode=True)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            r = await ac.get("/api/v1/server/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_server_info(self, api_client):
        """GET /api/v1/server/info returns server metadata."""
        r = await api_client.get("/api/v1/server/info")
        assert r.status_code == 200
        data = r.json()
        assert "server_name" in data
        assert "version" in data
        assert "mock_mode" in data


class TestStatus:
    @pytest.mark.asyncio
    async def test_get_status(self, api_client):
        """GET /api/v1/status returns full state snapshot."""
        r = await api_client.get("/api/v1/status")
        assert r.status_code == 200
        data = r.json()
        assert "layout_id" in data
        assert "cells" in data
        assert "audio" in data


class TestLayouts:
    @pytest.mark.asyncio
    async def test_list_layouts(self, api_client):
        """GET /api/v1/layouts returns the loaded layouts."""
        r = await api_client.get("/api/v1/layouts")
        assert r.status_code == 200
        layouts = r.json()
        ids = [lay["id"] for lay in layouts]
        assert "single" in ids
        assert "2x2" in ids

    @pytest.mark.asyncio
    async def test_apply_layout(self, api_client):
        """PUT /api/v1/layout switches the active layout."""
        r = await api_client.put("/api/v1/layout", json={"layout_id": "2x2"})
        assert r.status_code == 200
        status = await api_client.get("/api/v1/status")
        assert status.json()["layout_id"] == "2x2"

    @pytest.mark.asyncio
    async def test_apply_unknown_layout_returns_404(self, api_client):
        """PUT /api/v1/layout with unknown id returns 404."""
        r = await api_client.put("/api/v1/layout", json={"layout_id": "nonexistent"})
        assert r.status_code == 404


class TestSources:
    @pytest.mark.asyncio
    async def test_list_sources(self, api_client):
        """GET /api/v1/sources returns default sources."""
        r = await api_client.get("/api/v1/sources")
        assert r.status_code == 200
        ids = [s["id"] for s in r.json()]
        assert "espn" in ids

    @pytest.mark.asyncio
    async def test_create_source(self, api_client):
        """POST /api/v1/sources creates a new source."""
        r = await api_client.post(
            "/api/v1/sources",
            json={"name": "YouTube TV", "type": "url", "url": "https://tv.youtube.com"},
        )
        assert r.status_code == 201
        assert r.json()["id"] == "youtube-tv"

    @pytest.mark.asyncio
    async def test_update_source(self, api_client):
        """PUT /api/v1/sources/{id} updates an existing source."""
        r = await api_client.put("/api/v1/sources/espn", json={"notes": "Updated"})
        assert r.status_code == 200
        assert r.json()["notes"] == "Updated"

    @pytest.mark.asyncio
    async def test_delete_custom_source(self, api_client):
        """DELETE /api/v1/sources/{id} removes a custom source."""
        await api_client.post(
            "/api/v1/sources",
            json={"name": "My Stream", "type": "url", "url": "https://my.stream"},
        )
        r = await api_client.delete("/api/v1/sources/my-stream")
        assert r.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_preloaded_source_returns_409(self, api_client):
        """DELETE /api/v1/sources/{id} on a pre-loaded source returns 409."""
        r = await api_client.delete("/api/v1/sources/espn")
        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_get_unknown_source_returns_404(self, api_client):
        """GET /api/v1/sources/{id} for unknown source returns 404."""
        r = await api_client.get("/api/v1/sources/nonexistent")
        assert r.status_code == 404


class TestCells:
    @pytest.mark.asyncio
    async def test_assign_source_to_cell(self, api_client):
        """PUT /api/v1/cells/{id}/source assigns a source to a cell."""
        r = await api_client.put("/api/v1/cells/0/source", json={"source_id": "espn"})
        assert r.status_code == 200
        status = await api_client.get("/api/v1/status")
        cells = status.json()["cells"]
        assert cells[0]["source_id"] == "espn"

    @pytest.mark.asyncio
    async def test_clear_cell(self, api_client):
        """DELETE /api/v1/cells/{id}/source clears a cell."""
        await api_client.put("/api/v1/cells/0/source", json={"source_id": "espn"})
        r = await api_client.delete("/api/v1/cells/0/source")
        assert r.status_code == 204
        status = await api_client.get("/api/v1/status")
        assert status.json()["cells"][0]["source_id"] is None


class TestAudio:
    @pytest.mark.asyncio
    async def test_set_active_audio(self, api_client):
        """PUT /api/v1/audio/active sets the active audio cell."""
        r = await api_client.put("/api/v1/audio/active", json={"cell_index": 0})
        assert r.status_code == 200


class TestStubs:
    @pytest.mark.asyncio
    async def test_presets_returns_200(self, api_client):
        """Preset endpoints are implemented (Task 13)."""
        r = await api_client.get("/api/v1/presets")
        assert r.status_code == 200
        assert r.json() == []

    @pytest.mark.asyncio
    async def test_interactive_start_returns_200(self, api_client):
        """Interactive mode endpoints are implemented (Task 14)."""
        r = await api_client.post("/api/v1/interactive/start", json={"cell_index": 0})
        assert r.status_code == 200
        assert r.json()["is_active"] is True
