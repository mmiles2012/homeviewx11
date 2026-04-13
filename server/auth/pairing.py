"""Pairing manager — 6-digit code generation and validation."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from server.auth.tokens import TokenManager
from server.db import get_db

_CODE_EXPIRY_MINUTES = 5
_STATE_KEY_CODE = "pairing_code"
_STATE_KEY_EXPIRES = "pairing_expires_at"


class PairingManager:
    """Manages the pairing flow: generate code, validate, issue token."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self.token_manager = TokenManager(db_path)

    async def generate_pairing_code(self) -> str:
        """Generate a new 6-digit pairing code and persist it."""
        code = f"{secrets.randbelow(1_000_000):06d}"
        expires_at = (
            datetime.now(timezone.utc) + timedelta(minutes=_CODE_EXPIRY_MINUTES)
        ).isoformat()
        async with get_db(self._db_path) as conn:
            await conn.execute(
                "INSERT OR REPLACE INTO server_state (key, value) VALUES (?, ?)",
                (_STATE_KEY_CODE, code),
            )
            await conn.execute(
                "INSERT OR REPLACE INTO server_state (key, value) VALUES (?, ?)",
                (_STATE_KEY_EXPIRES, expires_at),
            )
            await conn.commit()
        return code

    async def get_current_code(self) -> dict | None:
        """Return {code, expires_at} if a valid code exists, else None."""
        async with get_db(self._db_path) as conn:
            cursor = await conn.execute(
                "SELECT value FROM server_state WHERE key = ?", (_STATE_KEY_CODE,)
            )
            code_row = await cursor.fetchone()
            cursor = await conn.execute(
                "SELECT value FROM server_state WHERE key = ?", (_STATE_KEY_EXPIRES,)
            )
            exp_row = await cursor.fetchone()

        if code_row is None or exp_row is None:
            return None

        expires_at = exp_row["value"]
        # Check expiry
        try:
            exp_dt = datetime.fromisoformat(expires_at)
            if datetime.now(timezone.utc) > exp_dt:
                return None
        except ValueError:
            return None

        return {"code": code_row["value"], "expires_at": expires_at}

    async def validate_code(self, code: str) -> str | None:
        """Validate a pairing code. Returns a Bearer token on success, else None."""
        current = await self.get_current_code()
        if current is None or current["code"] != code:
            return None

        # Consume the code and issue a token
        async with get_db(self._db_path) as conn:
            await conn.execute(
                "DELETE FROM server_state WHERE key IN (?, ?)",
                (_STATE_KEY_CODE, _STATE_KEY_EXPIRES),
            )
            await conn.commit()

        return await self.token_manager.create_token()

    async def is_paired(self) -> bool:
        """Return True if at least one active token exists."""
        return await self.token_manager.has_active_token()

    async def reset_pairing(self) -> str:
        """Revoke all tokens and generate a fresh pairing code."""
        await self.token_manager.revoke_all()
        return await self.generate_pairing_code()
