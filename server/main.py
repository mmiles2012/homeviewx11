"""HomeView server entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI

from server.auth.middleware import make_auth_dependency
from server.auth.pairing import PairingManager
from server.auth.tokens import TokenManager
from server.composition.cell import create_chromium_launcher
from server.composition.engine import CompositionEngine
from server.composition.layout import LayoutManager
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

    source_registry = SourceRegistry(resolved_db)

    layout_manager = LayoutManager()
    layout_manager.load_layouts(config.layouts_dir)

    window_manager = create_window_manager(mock_mode=resolved_mock, display_name=config.display)
    chromium_launcher = create_chromium_launcher(
        mock_mode=resolved_mock,
        profiles_dir=config.profiles_dir,
        chromium_binary=config.chromium_binary,
    )
    display_w = config.mock_display_width if resolved_mock else 1920
    display_h = config.mock_display_height if resolved_mock else 1080

    engine = CompositionEngine(
        layout_manager=layout_manager,
        window_manager=window_manager,
        chromium_launcher=chromium_launcher,
        source_registry=source_registry,
        display_width=display_w,
        display_height=display_h,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        from server.db import init_db
        await init_db(resolved_db)
        await engine.start()
        yield
        await engine.stop()

    app = FastAPI(title="HomeView", version="1.0.0", lifespan=lifespan)

    # Attach shared state
    app.state.token_manager = token_mgr
    app.state.pairing_manager = pairing_mgr
    app.state.engine = engine
    app.state.source_registry = source_registry
    app.state.db_path = resolved_db
    app.state.mock_mode = resolved_mock

    # Public routes (no auth)
    @app.get("/api/v1/server/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/pair/code")
    async def get_pair_code() -> dict:
        result = await pairing_mgr.get_current_code()
        if result is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Already paired or no active code")
        return result

    @app.post("/api/v1/pair")
    async def pair(body: dict) -> dict:
        from server.models import PairingRequest, PairingResponse
        from fastapi import HTTPException
        req = PairingRequest(**body)
        token = await pairing_mgr.validate_code(req.code)
        if token is None:
            raise HTTPException(status_code=401, detail="Invalid or expired pairing code")
        return PairingResponse(token=token).model_dump()

    # Protected routes — include router with global auth dependency
    from server.api.routes import router
    app.include_router(router, dependencies=[Depends(auth_dep)])

    return app


# Module-level app for uvicorn and tests that import `server.main.app`
app = create_app()


if __name__ == "__main__":
    import uvicorn

    config = get_config()
    uvicorn.run("server.main:app", host=config.host, port=config.port, reload=False)
