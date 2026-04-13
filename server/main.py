"""HomeView server entry point."""
from __future__ import annotations

from fastapi import Depends, FastAPI

from server.auth.middleware import make_auth_dependency
from server.auth.pairing import PairingManager
from server.auth.tokens import TokenManager
from server.config import get_config


def create_app(db_path: str | None = None, mock_mode: bool = False) -> FastAPI:
    """Create and configure the FastAPI application."""
    config = get_config()
    resolved_db = db_path or config.db_path

    token_mgr = TokenManager(resolved_db)
    pairing_mgr = PairingManager(resolved_db)
    auth_dep = make_auth_dependency(token_mgr)

    app = FastAPI(title="HomeView", version="1.0.0")

    # Attach managers to app state for use in routes
    app.state.token_manager = token_mgr
    app.state.pairing_manager = pairing_mgr
    app.state.db_path = resolved_db
    app.state.mock_mode = mock_mode or config.mock_mode

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

    @app.get("/api/v1/server/status", dependencies=[Depends(auth_dep)])
    async def server_status() -> dict:
        return {"status": "ok", "mock_mode": app.state.mock_mode}

    return app


# Module-level app for uvicorn / tests that import `server.main.app`
app = create_app()


if __name__ == "__main__":
    import uvicorn

    config = get_config()
    uvicorn.run("server.main:app", host=config.host, port=config.port, reload=False)
