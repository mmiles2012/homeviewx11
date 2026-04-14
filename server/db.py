"""Database initialization and connection management."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import aiosqlite

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('streaming', 'url')),
    url TEXT NOT NULL,
    icon_url TEXT,
    requires_widevine INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS presets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    layout_id TEXT NOT NULL,
    cell_assignments TEXT NOT NULL DEFAULT '{}',
    active_audio_cell INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS auth_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS server_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

_DEFAULT_SOURCES = [
    {
        "id": "espn",
        "name": "ESPN",
        "type": "streaming",
        "url": "https://espnplus.com",
        "icon_url": "https://a.espncdn.com/favicon.ico",
        "requires_widevine": 1,
        "notes": "Requires ESPN+ subscription",
    },
    {
        "id": "prime",
        "name": "Prime Video",
        "type": "streaming",
        "url": "https://www.amazon.com/gp/video/storefront",
        "icon_url": "https://m.media-amazon.com/images/G/01/digital/video/avod/icons/favicon.ico",
        "requires_widevine": 1,
        "notes": "Requires Prime subscription",
    },
    {
        "id": "netflix",
        "name": "Netflix",
        "type": "streaming",
        "url": "https://www.netflix.com/browse",
        "icon_url": "https://assets.nflxext.com/us/ffe/siteui/common/icons/nficon2016.ico",
        "requires_widevine": 1,
        "notes": "Requires Netflix subscription; Widevine L3 limits to 480p on Linux",
    },
]


async def init_db(db_path: str) -> None:
    """Create schema and seed default data if needed."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as conn:
        await conn.executescript(_SCHEMA)
        await _seed_defaults(conn)
        await conn.commit()


async def _seed_defaults(conn: aiosqlite.Connection) -> None:
    """Insert default sources if they don't exist yet."""
    for src in _DEFAULT_SOURCES:
        await conn.execute(
            """
            INSERT OR IGNORE INTO sources (id, name, type, url, icon_url, requires_widevine, notes)
            VALUES (:id, :name, :type, :url, :icon_url, :requires_widevine, :notes)
            """,
            src,
        )


@asynccontextmanager
async def get_db(db_path: str) -> AsyncGenerator[aiosqlite.Connection, None]:
    """Yield an aiosqlite connection to the database."""
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        yield conn
