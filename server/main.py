"""HomeView server entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server.api.events import EventBus
from server.audio.router import create_audio_router
from server.auth.middleware import make_auth_dependency
from server.presets.manager import PresetManager
from server.auth.pairing import PairingManager
from server.auth.tokens import TokenManager
from server.composition.cell import create_chromium_launcher
from server.composition.engine import CompositionEngine
from server.composition.display import detect_display_resolution
from server.composition.layout import LayoutManager
from server.composition.overlay import PairingOverlay
from server.composition.window import create_window_manager
from server.config import get_config
from server.sources.registry import SourceRegistry


def create_app(db_path: str | None = None, mock_mode: bool = False) -> FastAPI:
    """Create and configure the FastAPI application."""
    config = get_config()
    resolved_db = db_path or config.db_path
    resolved_mock = mock_mode or config.mock_mode

    token_mgr = TokenManager(resolved_db)
    pairing_mgr = PairingManager(resolved_db)
    auth_dep = make_auth_dependency(token_mgr)

    event_bus = EventBus()
    source_registry = SourceRegistry(resolved_db)

    layout_manager = LayoutManager()
    layout_manager.load_layouts(config.layouts_dir)

    window_manager = create_window_manager(
        mock_mode=resolved_mock, display_name=config.display
    )
    chromium_launcher = create_chromium_launcher(
        mock_mode=resolved_mock,
        profiles_dir=config.profiles_dir,
        chromium_binary=config.chromium_binary,
    )
    if resolved_mock:
        display_w = config.mock_display_width
        display_h = config.mock_display_height
    else:
        display_w, display_h = detect_display_resolution(display=config.display)

    audio_router = create_audio_router(mock_mode=resolved_mock)

    engine = CompositionEngine(
        layout_manager=layout_manager,
        window_manager=window_manager,
        chromium_launcher=chromium_launcher,
        source_registry=source_registry,
        audio_router=audio_router,
        display_width=display_w,
        display_height=display_h,
    )

    overlay_url = f"http://localhost:{config.port}/api/v1/pair/overlay"
    pairing_overlay = PairingOverlay(
        launcher=chromium_launcher, overlay_url=overlay_url
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        from server.db import init_db

        await init_db(resolved_db)

        # Wire engine state changes into the event bus
        def _on_state(state) -> None:
            import asyncio

            payload = {
                "layout_id": state.layout_id,
                "cells": [c.model_dump() for c in state.cells],
                "audio": state.audio.model_dump(),
            }
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(event_bus.emit("state.updated", payload))
            except RuntimeError:
                pass  # no running loop (e.g. during shutdown)

        def _on_health(event) -> None:
            import asyncio

            payload = {
                "cell_index": event.cell_index,
                "event_type": event.event_type,
                "detail": event.detail,
            }
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(event_bus.emit("cell.health", payload))
            except RuntimeError:
                pass

        await audio_router.setup()
        engine.on_state_change(_on_state)
        engine.on_health_event(_on_health)
        await engine.start()

        # Auto-generate pairing code on first boot if not already paired
        if not await pairing_mgr.is_paired():
            await pairing_mgr.generate_pairing_code()
            await pairing_overlay.show()

        yield
        await engine.stop()
        await audio_router.cleanup()

    app = FastAPI(title="HomeView", version="1.0.0", lifespan=lifespan)

    # CORS — allow localhost:5173 for dev; all origins in mock mode
    cors_origins = ["*"] if resolved_mock else ["http://localhost:5173"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    preset_mgr = PresetManager(db_path=resolved_db, engine=engine)

    # Attach shared state
    app.state.token_manager = token_mgr
    app.state.pairing_manager = pairing_mgr
    app.state.engine = engine
    app.state.source_registry = source_registry
    app.state.event_bus = event_bus
    app.state.preset_manager = preset_mgr
    app.state.db_path = resolved_db
    app.state.mock_mode = resolved_mock
    app.state.pairing_overlay = pairing_overlay

    # Public routes (no auth)
    @app.get("/api/v1/server/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/pair/code")
    async def get_pair_code() -> dict:
        result = await pairing_mgr.get_current_code()
        if result is None:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "NOT_PAIRED_OR_EXPIRED",
                        "message": "No active pairing code",
                        "details": {},
                    }
                },
            )
        return result

    @app.post("/api/v1/pair")
    async def pair(body: dict) -> dict:
        from server.models import PairingRequest, PairingResponse
        from fastapi import HTTPException

        if await pairing_mgr.is_paired():
            raise HTTPException(
                status_code=409,
                detail={
                    "error": {
                        "code": "ALREADY_PAIRED",
                        "message": "Server already has an active pairing",
                        "details": {},
                    }
                },
            )
        req = PairingRequest(**body)
        token = await pairing_mgr.validate_code(req.code)
        if token is None:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": {
                        "code": "INVALID_PAIRING_CODE",
                        "message": "Invalid or expired pairing code",
                        "details": {},
                    }
                },
            )
        token_value = token
        await pairing_overlay.close()
        return PairingResponse(token=token_value).model_dump()

    @app.get("/api/v1/pair/overlay")
    async def pair_overlay() -> dict:
        from fastapi.responses import HTMLResponse

        code_info = await pairing_mgr.get_current_code()
        code = code_info["code"] if code_info else "------"
        html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>HomeView Pairing</title>
<style>
  body {{
    margin: 0; display: flex; align-items: center; justify-content: center;
    min-height: 100vh; background: #0A0A0F; color: #E8E8F0;
    font-family: system-ui, sans-serif; text-align: center;
  }}
  .code {{
    font-size: 10vw; font-weight: 700; letter-spacing: 0.15em;
    color: #7C6AF7; margin: 0.5em 0;
  }}
  h1 {{ font-size: 3vw; margin-bottom: 0.25em; }}
  p {{ font-size: 2vw; color: #8888A0; }}
</style>
</head>
<body>
  <div>
    <h1>HomeView</h1>
    <div class="code">{code}</div>
    <p>Enter this code in the HomeView app to pair your device.</p>
  </div>
</body>
</html>"""
        return HTMLResponse(content=html)

    # Protected routes — include router with global auth dependency
    from server.api.routes import router

    app.include_router(router, dependencies=[Depends(auth_dep)])

    # WebSocket (auth handled inside the handler via query param)
    from server.api.websocket import ws_router

    app.include_router(ws_router)

    # Static file serving — mount after API routes to avoid shadowing.
    # Only mounted when index.html exists; server starts fine without it.
    _static_dir = Path(__file__).parent / "static"
    if (_static_dir / "index.html").exists():
        app.mount(
            "/", StaticFiles(directory=str(_static_dir), html=True), name="static"
        )

    return app


# Module-level app for uvicorn and tests that import `server.main.app`
app = create_app()


if __name__ == "__main__":
    import uvicorn

    config = get_config()
    uvicorn.run("server.main:app", host=config.host, port=config.port, reload=False)
