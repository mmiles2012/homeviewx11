"""Tests for database initialization and schema."""
import os
import pytest
import aiosqlite

from server.db import init_db, get_db


@pytest.mark.asyncio
async def test_db_creates_tables(tmp_path):
    """Database initializes all required tables."""
    db_path = str(tmp_path / "test.db")
    await init_db(db_path)

    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in await cursor.fetchall()}

    assert "sources" in tables
    assert "presets" in tables
    assert "auth_tokens" in tables
    assert "server_state" in tables


@pytest.mark.asyncio
async def test_db_seeds_default_sources(tmp_path):
    """Default sources (ESPN, Prime, Netflix) are seeded on first run."""
    db_path = str(tmp_path / "test.db")
    await init_db(db_path)

    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute("SELECT id FROM sources ORDER BY id")
        ids = {row["id"] for row in await cursor.fetchall()}

    assert "espn" in ids
    assert "prime" in ids
    assert "netflix" in ids


@pytest.mark.asyncio
async def test_db_idempotent(tmp_path):
    """Calling init_db twice does not fail or duplicate seeds."""
    db_path = str(tmp_path / "test.db")
    await init_db(db_path)
    await init_db(db_path)  # should not raise

    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM sources WHERE id='espn'")
        count = (await cursor.fetchone())[0]

    assert count == 1


@pytest.mark.asyncio
async def test_db_custom_path(tmp_path):
    """Database is created at the specified path."""
    db_path = str(tmp_path / "subdir" / "homeview.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    await init_db(db_path)
    assert os.path.exists(db_path)


@pytest.mark.asyncio
async def test_get_db_yields_connection(tmp_path):
    """get_db yields a working aiosqlite connection."""
    db_path = str(tmp_path / "test.db")
    await init_db(db_path)

    async with get_db(db_path) as conn:
        cursor = await conn.execute("SELECT 1")
        row = await cursor.fetchone()

    assert row[0] == 1
