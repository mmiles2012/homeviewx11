"""Tests for pairing flow, token management, and auth middleware."""

import pytest
from httpx import AsyncClient, ASGITransport

from server.db import init_db
from server.auth.pairing import PairingManager
from server.auth.tokens import TokenManager


@pytest.fixture
async def db_path(tmp_path) -> str:
    path = str(tmp_path / "test.db")
    await init_db(path)
    return path


@pytest.fixture
async def token_mgr(db_path) -> TokenManager:
    return TokenManager(db_path)


@pytest.fixture
async def pairing_mgr(db_path) -> PairingManager:
    return PairingManager(db_path)


class TestTokenManager:
    @pytest.mark.asyncio
    async def test_create_and_validate_token(self, token_mgr):
        """Created token validates successfully."""
        token = await token_mgr.create_token()
        assert len(token) >= 32
        assert await token_mgr.validate_token(token) is True

    @pytest.mark.asyncio
    async def test_invalid_token_fails(self, token_mgr):
        """Unknown token is rejected."""
        assert await token_mgr.validate_token("bogus") is False

    @pytest.mark.asyncio
    async def test_token_stored_as_hash(self, token_mgr, db_path):
        """Token is stored as SHA-256 hash, not plaintext."""
        import aiosqlite

        token = await token_mgr.create_token()
        async with aiosqlite.connect(db_path) as conn:
            cursor = await conn.execute("SELECT token FROM auth_tokens")
            row = await cursor.fetchone()
        assert row is not None
        assert row[0] != token  # plaintext not stored
        assert len(row[0]) == 64  # SHA-256 hex digest

    @pytest.mark.asyncio
    async def test_revoke_all_tokens(self, token_mgr):
        """revoke_all() deactivates all tokens."""
        token = await token_mgr.create_token()
        await token_mgr.revoke_all()
        assert await token_mgr.validate_token(token) is False

    @pytest.mark.asyncio
    async def test_has_active_token(self, token_mgr):
        """has_active_token() returns True when a valid token exists."""
        assert await token_mgr.has_active_token() is False
        await token_mgr.create_token()
        assert await token_mgr.has_active_token() is True


class TestPairingManager:
    @pytest.mark.asyncio
    async def test_generate_pairing_code_is_6_digits(self, pairing_mgr):
        """Generated pairing code is exactly 6 digits."""
        code = await pairing_mgr.generate_pairing_code()
        assert len(code) == 6
        assert code.isdigit()

    @pytest.mark.asyncio
    async def test_get_current_code_returns_code_when_not_paired(self, pairing_mgr):
        """get_current_code() returns code+expires_at when in pairing mode."""
        await pairing_mgr.generate_pairing_code()
        result = await pairing_mgr.get_current_code()
        assert result is not None
        assert "code" in result
        assert "expires_at" in result

    @pytest.mark.asyncio
    async def test_validate_correct_code_returns_token(self, pairing_mgr):
        """Correct pairing code returns a Bearer token."""
        code = await pairing_mgr.generate_pairing_code()
        token = await pairing_mgr.validate_code(code)
        assert token is not None
        assert len(token) >= 32

    @pytest.mark.asyncio
    async def test_validate_wrong_code_returns_none(self, pairing_mgr):
        """Wrong pairing code returns None."""
        await pairing_mgr.generate_pairing_code()
        result = await pairing_mgr.validate_code("000000")
        assert result is None

    @pytest.mark.asyncio
    async def test_reset_pairing_clears_tokens(self, pairing_mgr):
        """reset_pairing() deactivates all tokens and generates a new code."""
        code = await pairing_mgr.generate_pairing_code()
        token = await pairing_mgr.validate_code(code)
        assert token is not None

        await pairing_mgr.reset_pairing()
        assert await pairing_mgr.token_manager.validate_token(token) is False
        new_code = await pairing_mgr.get_current_code()
        assert new_code is not None

    @pytest.mark.asyncio
    async def test_is_paired_false_before_pairing(self, pairing_mgr):
        """is_paired() is False before any token is created."""
        assert await pairing_mgr.is_paired() is False

    @pytest.mark.asyncio
    async def test_is_paired_true_after_successful_pair(self, pairing_mgr):
        """is_paired() is True after a successful pairing."""
        code = await pairing_mgr.generate_pairing_code()
        await pairing_mgr.validate_code(code)
        assert await pairing_mgr.is_paired() is True


class TestAuthMiddleware:
    @pytest.mark.asyncio
    async def test_unauthenticated_request_returns_401(self, db_path):
        """Requests without a valid token return 401 on protected endpoints."""
        from server.main import create_app

        app = create_app(db_path=db_path, mock_mode=True)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            async with app.router.lifespan_context(app):
                response = await ac.get("/api/v1/status")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_pairing_endpoint_accessible_without_token(self, db_path):
        """POST /api/v1/pair and GET /api/v1/pair/code do not require auth."""
        from server.main import create_app

        app = create_app(db_path=db_path, mock_mode=True)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            async with app.router.lifespan_context(app):
                response = await ac.get("/api/v1/pair/code")
        # 200 (code available) or 404 (already paired) — not 401
        assert response.status_code != 401

    @pytest.mark.asyncio
    async def test_authenticated_request_succeeds(self, db_path):
        """Valid Bearer token allows access to protected endpoints."""
        from server.main import create_app
        from server.auth.pairing import PairingManager

        pairing = PairingManager(db_path)
        code = await pairing.generate_pairing_code()
        token = await pairing.validate_code(code)

        app = create_app(db_path=db_path, mock_mode=True)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            async with app.router.lifespan_context(app):
                response = await ac.get(
                    "/api/v1/status",
                    headers={"Authorization": f"Bearer {token}"},
                )
        assert response.status_code == 200
