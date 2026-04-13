"""Source registry — CRUD over the sources SQLite table."""
from __future__ import annotations

import re

from server.db import get_db
from server.models import Source, SourceCreate, SourceUpdate

# IDs of pre-loaded sources that cannot be deleted
_PRELOADED_IDS = frozenset({"espn", "prime", "netflix"})


class SourceNotFoundError(Exception):
    """Raised when a requested source does not exist."""


class SourceAlreadyExistsError(Exception):
    """Raised when a source with the same id already exists."""


def _slugify(name: str) -> str:
    """Convert a display name to a URL-safe slug id."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def _row_to_source(row) -> Source:
    return Source(
        id=row["id"],
        name=row["name"],
        type=row["type"],
        url=row["url"],
        icon_url=row["icon_url"],
        requires_widevine=bool(row["requires_widevine"]),
        notes=row["notes"],
    )


class SourceRegistry:
    """Async CRUD for the source registry."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def list_sources(self) -> list[Source]:
        """Return all sources ordered by name."""
        async with get_db(self._db_path) as conn:
            cursor = await conn.execute("SELECT * FROM sources ORDER BY name")
            rows = await cursor.fetchall()
        return [_row_to_source(r) for r in rows]

    async def get_source(self, source_id: str) -> Source:
        """Return a single source by id, or raise SourceNotFoundError."""
        async with get_db(self._db_path) as conn:
            cursor = await conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,))
            row = await cursor.fetchone()
        if row is None:
            raise SourceNotFoundError(f"Source '{source_id}' not found")
        return _row_to_source(row)

    async def create_source(self, data: SourceCreate) -> Source:
        """Insert a new custom source and return it."""
        source_id = _slugify(data.name)
        async with get_db(self._db_path) as conn:
            # Check for collision
            cursor = await conn.execute("SELECT id FROM sources WHERE id = ?", (source_id,))
            if await cursor.fetchone() is not None:
                raise SourceAlreadyExistsError(f"Source '{source_id}' already exists")
            await conn.execute(
                """
                INSERT INTO sources (id, name, type, url, icon_url, requires_widevine, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    data.name,
                    data.type,
                    data.url,
                    data.icon_url,
                    int(data.requires_widevine),
                    data.notes,
                ),
            )
            await conn.commit()
        return await self.get_source(source_id)

    async def update_source(self, source_id: str, data: SourceUpdate) -> Source:
        """Update a source's fields and refresh updated_at."""
        # Confirm it exists first
        await self.get_source(source_id)

        updates = {k: v for k, v in data.model_dump().items() if v is not None}
        if not updates:
            return await self.get_source(source_id)

        set_clauses = ", ".join(f"{col} = ?" for col in updates)
        values = list(updates.values()) + [source_id]

        async with get_db(self._db_path) as conn:
            await conn.execute(
                f"UPDATE sources SET {set_clauses}, updated_at = datetime('now') WHERE id = ?",  # noqa: S608
                values,
            )
            await conn.commit()
        return await self.get_source(source_id)

    async def delete_source(self, source_id: str) -> None:
        """Delete a custom source. Raises ValueError for pre-loaded sources."""
        if source_id in _PRELOADED_IDS:
            raise ValueError(f"cannot delete pre-loaded source '{source_id}'")
        # Confirm it exists
        await self.get_source(source_id)
        async with get_db(self._db_path) as conn:
            await conn.execute("DELETE FROM sources WHERE id = ?", (source_id,))
            await conn.commit()
