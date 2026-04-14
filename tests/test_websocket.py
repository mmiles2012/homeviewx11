"""Tests for WebSocket endpoint and event broadcasting."""
import pytest

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


class TestEventBus:
    @pytest.mark.asyncio
    async def test_subscribe_receives_emitted_events(self):
        """Subscribers receive events emitted to the bus."""
        import asyncio
        from server.api.events import EventBus

        bus = EventBus()
        queue = bus.subscribe()
        await bus.emit("state.updated", {"layout_id": "single"})
        event = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert event["type"] == "state.updated"
        assert event["data"]["layout_id"] == "single"

    @pytest.mark.asyncio
    async def test_multiple_subscribers_all_receive(self):
        """All subscribers receive broadcast events."""
        import asyncio
        from server.api.events import EventBus

        bus = EventBus()
        q1 = bus.subscribe()
        q2 = bus.subscribe()
        await bus.emit("state.updated", {"layout_id": "2x2"})
        e1 = await asyncio.wait_for(q1.get(), timeout=1.0)
        e2 = await asyncio.wait_for(q2.get(), timeout=1.0)
        assert e1["type"] == "state.updated"
        assert e2["type"] == "state.updated"

    @pytest.mark.asyncio
    async def test_unsubscribe_stops_delivery(self):
        """Unsubscribed queues no longer receive events."""
        import asyncio
        from server.api.events import EventBus

        bus = EventBus()
        queue = bus.subscribe()
        bus.unsubscribe(queue)
        await bus.emit("state.updated", {"layout_id": "single"})
        # Queue should be empty (event not delivered)
        await asyncio.sleep(0.05)
        assert queue.empty()


class TestWebSocketAuth:
    @pytest.mark.asyncio
    async def test_ws_requires_token(self, db_path):
        """WebSocket connection without token is rejected with close code 4001."""
        from starlette.testclient import TestClient
        from starlette.websockets import WebSocketDisconnect
        from server.main import create_app
        app = create_app(db_path=db_path, mock_mode=True)
        with TestClient(app) as client:
            with pytest.raises(WebSocketDisconnect) as exc_info:
                with client.websocket_connect("/ws/control") as ws:
                    ws.receive_json()
        assert exc_info.value.code == 4001

    @pytest.mark.asyncio
    async def test_ws_token_query_param_accepted(self, db_path, auth_token):
        """WebSocket connection with valid token query param is accepted."""
        from starlette.testclient import TestClient
        from server.main import create_app
        app = create_app(db_path=db_path, mock_mode=True)
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/control?token={auth_token}") as ws:
                # Should receive the initial state snapshot
                data = ws.receive_json()
                assert data["type"] == "state.updated"

    @pytest.mark.asyncio
    async def test_ws_invalid_token_rejected(self, db_path):
        """WebSocket connection with invalid token is rejected."""
        from starlette.testclient import TestClient
        from server.main import create_app
        app = create_app(db_path=db_path, mock_mode=True)
        with TestClient(app) as client:
            with pytest.raises(Exception):
                with client.websocket_connect("/ws/control?token=bogus") as ws:
                    ws.receive_json()


class TestWebSocketEvents:
    @pytest.mark.asyncio
    async def test_state_updated_on_layout_change(self, db_path, auth_token):
        """state.updated event fires when layout changes via API."""
        from starlette.testclient import TestClient
        from server.main import create_app
        app = create_app(db_path=db_path, mock_mode=True)
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/control?token={auth_token}") as ws:
                # Consume initial state event
                ws.receive_json()
                # Change layout via REST API
                r = client.put(
                    "/api/v1/layout",
                    json={"layout_id": "2x2"},
                    headers={"Authorization": f"Bearer {auth_token}"},
                )
                assert r.status_code == 200
                # Should receive state.updated event
                event = ws.receive_json()
                assert event["type"] == "state.updated"
                assert event["data"]["layout_id"] == "2x2"

    @pytest.mark.asyncio
    async def test_state_updated_on_audio_change(self, db_path, auth_token):
        """state.updated event fires when audio cell changes."""
        from starlette.testclient import TestClient
        from server.main import create_app
        app = create_app(db_path=db_path, mock_mode=True)
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/control?token={auth_token}") as ws:
                ws.receive_json()  # initial
                client.put(
                    "/api/v1/audio/active",
                    json={"cell_index": 0},
                    headers={"Authorization": f"Bearer {auth_token}"},
                )
                event = ws.receive_json()
                assert event["type"] == "state.updated"
                assert event["data"]["audio"]["active_cell"] == 0

    @pytest.mark.asyncio
    async def test_multiple_clients_all_notified(self, db_path, auth_token):
        """All connected WebSocket clients receive broadcast events."""
        from starlette.testclient import TestClient
        from server.main import create_app
        app = create_app(db_path=db_path, mock_mode=True)
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/control?token={auth_token}") as ws1:
                with client.websocket_connect(f"/ws/control?token={auth_token}") as ws2:
                    ws1.receive_json()  # initial for ws1
                    ws2.receive_json()  # initial for ws2
                    client.put(
                        "/api/v1/layout",
                        json={"layout_id": "2x2"},
                        headers={"Authorization": f"Bearer {auth_token}"},
                    )
                    e1 = ws1.receive_json()
                    e2 = ws2.receive_json()
                    assert e1["type"] == "state.updated"
                    assert e2["type"] == "state.updated"
