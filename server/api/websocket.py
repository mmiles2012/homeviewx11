"""WebSocket endpoint for real-time state updates."""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from server.api.events import EventBus
from server.auth.tokens import TokenManager

logger = logging.getLogger(__name__)

ws_router = APIRouter()


async def _authenticate(websocket: WebSocket, token_manager: TokenManager) -> bool:
    """Return True if the connection carries a valid token."""
    # Check query param first
    token = websocket.query_params.get("token")
    if token and await token_manager.validate_token(token):
        return True
    return False


@ws_router.websocket("/ws/control")
async def websocket_control(websocket: WebSocket) -> None:
    """Real-time state and health event stream."""
    token_manager: TokenManager = websocket.app.state.token_manager
    event_bus: EventBus = websocket.app.state.event_bus

    if not await _authenticate(websocket, token_manager):
        await websocket.close(code=4001)
        return

    await websocket.accept()

    queue = event_bus.subscribe()
    try:
        # Send initial state snapshot
        engine = websocket.app.state.engine
        state = engine.get_state()
        await websocket.send_json({
            "type": "state.updated",
            "data": {
                "layout_id": state.layout_id,
                "cells": [c.model_dump() for c in state.cells],
                "audio": state.audio.model_dump(),
            },
        })

        # Relay events until client disconnects
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                if websocket.client_state == WebSocketState.DISCONNECTED:
                    break
                await websocket.send_json(event)
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                if websocket.client_state != WebSocketState.DISCONNECTED:
                    try:
                        await websocket.send_json({"type": "ping"})
                    except Exception:
                        break
    except WebSocketDisconnect:
        pass
    finally:
        event_bus.unsubscribe(queue)
