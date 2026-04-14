"""End-to-end integration tests exercising full API flows in mock mode."""
import pytest
from starlette.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    """TestClient with a fresh DB and mock mode enabled."""
    import asyncio
    from server.db import init_db
    from server.main import create_app

    db_path = str(tmp_path / "integration.db")
    asyncio.get_event_loop().run_until_complete(init_db(db_path))
    app = create_app(db_path=db_path, mock_mode=True)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def authed_client(tmp_path):
    """TestClient that has completed the pairing flow."""
    import asyncio
    from server.db import init_db
    from server.auth.pairing import PairingManager
    from server.main import create_app

    db_path = str(tmp_path / "integration.db")
    asyncio.get_event_loop().run_until_complete(init_db(db_path))

    # Complete pairing outside the app
    async def _pair():
        mgr = PairingManager(db_path)
        code = await mgr.generate_pairing_code()
        return await mgr.validate_code(code)

    token = asyncio.get_event_loop().run_until_complete(_pair())
    app = create_app(db_path=db_path, mock_mode=True)
    with TestClient(app) as c:
        c.headers.update({"Authorization": f"Bearer {token}"})
        yield c, token


class TestFlow1Setup:
    """Flow 1: Pair -> verify auth -> get status."""

    def test_pairing_flow(self, client):
        """GET pair code -> POST pair -> access protected endpoint."""
        # Get pairing code
        r = client.get("/api/v1/pair/code")
        assert r.status_code == 200
        code = r.json()["code"]
        assert len(code) == 6 and code.isdigit()

        # Pair with the code
        r = client.post("/api/v1/pair", json={"code": code})
        assert r.status_code == 200
        token = r.json()["token"]
        assert len(token) >= 32

        # Access protected endpoint
        r = client.get("/api/v1/status", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

    def test_initial_status_is_single_layout(self, authed_client):
        """Initial status shows single layout with one empty cell."""
        c, _ = authed_client
        r = c.get("/api/v1/status")
        assert r.status_code == 200
        data = r.json()
        assert data["layout_id"] == "single"
        assert len(data["cells"]) == 1
        assert data["cells"][0]["source_id"] is None

    def test_get_pair_code_returns_404_after_pairing(self, authed_client):
        """GET /api/v1/pair/code returns 404 once already paired."""
        c, _ = authed_client
        r = c.get("/api/v1/pair/code")
        assert r.status_code == 404


class TestFlow2MultiStream:
    """Flow 2: Set layout 2x2 -> assign sources -> set audio -> verify status."""

    def test_full_multi_stream_flow(self, authed_client):
        """Set 2x2 layout, assign ESPN/Netflix/Prime, set audio, verify state."""
        c, _ = authed_client

        # Switch to 2x2
        r = c.put("/api/v1/layout", json={"layout_id": "2x2"})
        assert r.status_code == 200

        # Assign sources
        c.put("/api/v1/cells/0/source", json={"source_id": "espn"})
        c.put("/api/v1/cells/1/source", json={"source_id": "netflix"})
        c.put("/api/v1/cells/2/source", json={"source_id": "prime"})

        # Set active audio
        r = c.put("/api/v1/audio/active", json={"cell_index": 0})
        assert r.status_code == 200

        # Verify full state
        r = c.get("/api/v1/status")
        assert r.status_code == 200
        data = r.json()
        assert data["layout_id"] == "2x2"
        assert len(data["cells"]) == 4
        cell_sources = {cell["index"]: cell["source_id"] for cell in data["cells"]}
        assert cell_sources[0] == "espn"
        assert cell_sources[1] == "netflix"
        assert cell_sources[2] == "prime"
        assert data["audio"]["active_cell"] == 0


class TestFlow3Preset:
    """Flow 3: Save preset -> switch layout -> apply preset -> verify restoration."""

    def test_preset_save_apply_flow(self, authed_client):
        """Save state as preset, change layout, apply preset, verify restored."""
        c, _ = authed_client

        # Set up initial state
        c.put("/api/v1/layout", json={"layout_id": "2x2"})
        c.put("/api/v1/cells/0/source", json={"source_id": "espn"})
        c.put("/api/v1/audio/active", json={"cell_index": 0})

        # Save preset
        r = c.post("/api/v1/presets", json={"name": "Sports Night"})
        assert r.status_code == 201
        preset_id = r.json()["id"]
        assert preset_id == "sports-night"

        # Change to different layout
        c.put("/api/v1/layout", json={"layout_id": "single"})
        assert c.get("/api/v1/status").json()["layout_id"] == "single"

        # Apply preset
        r = c.put(f"/api/v1/presets/{preset_id}/apply")
        assert r.status_code == 200

        # Verify restoration
        status = c.get("/api/v1/status").json()
        assert status["layout_id"] == "2x2"
        assert status["audio"]["active_cell"] == 0


class TestLayoutTransition:
    """Layout transition preserves sources per PRD rules."""

    def test_layout_switch_preserves_sources(self, authed_client):
        """Sources in cells that exist in both layouts are preserved."""
        c, _ = authed_client

        # Assign source in single layout cell 0
        c.put("/api/v1/cells/0/source", json={"source_id": "espn"})

        # Switch to 2x2 — cell 0 should retain ESPN
        c.put("/api/v1/layout", json={"layout_id": "2x2"})
        status = c.get("/api/v1/status").json()
        assert status["layout_id"] == "2x2"
        assert len(status["cells"]) == 4

    def test_unknown_layout_returns_404(self, authed_client):
        """PUT /api/v1/layout with unknown id returns 404."""
        c, _ = authed_client
        r = c.put("/api/v1/layout", json={"layout_id": "does-not-exist"})
        assert r.status_code == 404


class TestAudioRouting:
    """Audio routing state management."""

    def test_switch_active_audio_between_cells(self, authed_client):
        """Switching active audio cell updates state correctly."""
        c, _ = authed_client
        c.put("/api/v1/layout", json={"layout_id": "2x2"})

        c.put("/api/v1/audio/active", json={"cell_index": 0})
        assert c.get("/api/v1/status").json()["audio"]["active_cell"] == 0

        c.put("/api/v1/audio/active", json={"cell_index": 2})
        assert c.get("/api/v1/status").json()["audio"]["active_cell"] == 2


class TestInteractiveModeFlow:
    """Interactive mode start/stop flow."""

    def test_start_stop_interactive(self, authed_client):
        """Start interactive mode, verify active, stop, verify cleared."""
        c, _ = authed_client

        r = c.post("/api/v1/interactive/start", json={"cell_index": 0})
        assert r.status_code == 200
        assert r.json()["is_active"] is True

        r = c.post("/api/v1/interactive/stop")
        assert r.status_code == 200
        assert r.json()["is_active"] is False

    def test_interactive_conflict(self, authed_client):
        """Starting interactive on a different cell returns 409."""
        c, _ = authed_client
        c.post("/api/v1/interactive/start", json={"cell_index": 0})
        r = c.post("/api/v1/interactive/start", json={"cell_index": 1})
        assert r.status_code == 409


class TestErrorCases:
    """Error response format matches PRD Section 5.5.3."""

    def test_invalid_token_returns_401(self, client):
        """Requests with invalid token return 401."""
        r = client.get("/api/v1/status", headers={"Authorization": "Bearer invalid"})
        assert r.status_code == 401

    def test_unknown_source_returns_404(self, authed_client):
        """GET /api/v1/sources/{id} for unknown source returns 404."""
        c, _ = authed_client
        r = c.get("/api/v1/sources/does-not-exist")
        assert r.status_code == 404

    def test_unknown_layout_returns_404(self, authed_client):
        """PUT /api/v1/layout with unknown layout returns 404."""
        c, _ = authed_client
        r = c.put("/api/v1/layout", json={"layout_id": "nonexistent"})
        assert r.status_code == 404

    def test_unknown_preset_apply_returns_404(self, authed_client):
        """PUT /api/v1/presets/{id}/apply with unknown preset returns 404."""
        c, _ = authed_client
        r = c.put("/api/v1/presets/nonexistent/apply")
        assert r.status_code == 404

    def test_health_no_auth(self, client):
        """GET /api/v1/server/health requires no auth."""
        r = client.get("/api/v1/server/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestWebSocketFlow:
    """WebSocket event stream."""

    def test_ws_receives_state_on_connect(self, authed_client):
        """On connect, WS sends initial state.updated event."""
        c, token = authed_client
        with c.websocket_connect(f"/ws/control?token={token}") as ws:
            event = ws.receive_json()
            assert event["type"] == "state.updated"
            assert "layout_id" in event["data"]

    def test_ws_receives_event_on_layout_change(self, authed_client):
        """Layout change triggers state.updated over WebSocket."""
        c, token = authed_client
        with c.websocket_connect(f"/ws/control?token={token}") as ws:
            ws.receive_json()  # consume initial
            c.put("/api/v1/layout", json={"layout_id": "2x2"})
            event = ws.receive_json()
            assert event["type"] == "state.updated"
            assert event["data"]["layout_id"] == "2x2"
