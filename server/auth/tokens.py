"""Token management — create, validate, and revoke Bearer tokens."""
from __future__ import annotations

import hashlib
import secrets


from server.db import get_db


def _hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of a token."""
    return hashlib.sha256(token.encode()).hexdigest()


class TokenManager:
    """Manages Bearer tokens stored as SHA-256 hashes in SQLite."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def create_token(self) -> str:
        """Generate a secure random token, store its hash, return the plaintext."""
        token = secrets.token_urlsafe(32)
        token_hash = _hash_token(token)
        async with get_db(self._db_path) as conn:
            await conn.execute(
                "INSERT INTO auth_tokens (token) VALUES (?)", (token_hash,)
            )
            await conn.commit()
        return token

    async def validate_token(self, token: str) -> bool:
        """Return True if the token matches an active DB record."""
        token_hash = _hash_token(token)
        async with get_db(self._db_path) as conn:
            cursor = await conn.execute(
                "SELECT id FROM auth_tokens WHERE token = ? AND is_active = 1",
                (token_hash,),
            )
            row = await cursor.fetchone()
        return row is not None

    async def revoke_all(self) -> None:
        """Deactivate all tokens."""
        async with get_db(self._db_path) as conn:
            await conn.execute("UPDATE auth_tokens SET is_active = 0")
            await conn.commit()

    async def has_active_token(self) -> bool:
        """Return True if at least one active token exists."""
        async with get_db(self._db_path) as conn:
            cursor = await conn.execute(
                "SELECT id FROM auth_tokens WHERE is_active = 1 LIMIT 1"
            )
            row = await cursor.fetchone()
        return row is not None
