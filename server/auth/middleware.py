"""FastAPI auth dependency — validates Bearer tokens."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from server.auth.tokens import TokenManager

_bearer_scheme = HTTPBearer(auto_error=False)

# Endpoints that skip auth
_PUBLIC_PATHS = {
    "/api/v1/pair",
    "/api/v1/pair/code",
    "/api/v1/server/health",
}


def make_auth_dependency(token_manager: TokenManager):
    """Return a FastAPI dependency that validates Bearer tokens."""

    async def require_auth(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    ) -> None:
        if request.url.path in _PUBLIC_PATHS:
            return
        if credentials is None:
            raise HTTPException(status_code=401, detail="Missing Bearer token")
        if not await token_manager.validate_token(credentials.credentials):
            raise HTTPException(status_code=401, detail="Invalid or expired token")

    return require_auth
