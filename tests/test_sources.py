"""Tests for the source registry."""

import pytest

from server.db import init_db
from server.sources.registry import (
    SourceRegistry,
    SourceNotFoundError,
    SourceAlreadyExistsError,
)
from server.models import SourceCreate, SourceUpdate


@pytest.fixture
async def registry(tmp_path) -> SourceRegistry:
    """Registry backed by a fresh temporary database."""
    db_path = str(tmp_path / "test.db")
    await init_db(db_path)
    return SourceRegistry(db_path)


@pytest.mark.asyncio
async def test_list_sources_returns_defaults(registry):
    """list_sources returns ESPN, Prime, Netflix by default."""
    sources = await registry.list_sources()
    ids = {s.id for s in sources}
    assert "espn" in ids
    assert "prime" in ids
    assert "netflix" in ids


@pytest.mark.asyncio
async def test_get_source_returns_source(registry):
    """get_source returns a Source by id."""
    source = await registry.get_source("espn")
    assert source.id == "espn"
    assert source.name == "ESPN"


@pytest.mark.asyncio
async def test_get_source_not_found_raises(registry):
    """get_source raises SourceNotFoundError for unknown id."""
    with pytest.raises(SourceNotFoundError):
        await registry.get_source("nonexistent")


@pytest.mark.asyncio
async def test_create_source(registry):
    """create_source adds a new custom source."""
    data = SourceCreate(name="YouTube TV", type="url", url="https://tv.youtube.com")
    source = await registry.create_source(data)
    assert source.id == "youtube-tv"
    assert source.name == "YouTube TV"
    assert source.type == "url"

    # Verify it's persisted
    fetched = await registry.get_source("youtube-tv")
    assert fetched.name == "YouTube TV"


@pytest.mark.asyncio
async def test_create_source_duplicate_raises(registry):
    """create_source raises SourceAlreadyExistsError for duplicate id."""
    data = SourceCreate(name="ESPN", type="url", url="https://espn.com")
    with pytest.raises(SourceAlreadyExistsError):
        await registry.create_source(data)


@pytest.mark.asyncio
async def test_update_source(registry):
    """update_source modifies fields and updates updated_at."""
    updated = await registry.update_source("espn", SourceUpdate(notes="Updated note"))
    assert updated.notes == "Updated note"


@pytest.mark.asyncio
async def test_update_source_not_found_raises(registry):
    """update_source raises SourceNotFoundError for unknown id."""
    with pytest.raises(SourceNotFoundError):
        await registry.update_source("ghost", SourceUpdate(name="Ghost"))


@pytest.mark.asyncio
async def test_delete_custom_source(registry):
    """delete_source removes a custom (url-type) source."""
    data = SourceCreate(name="My Stream", type="url", url="https://my.stream")
    await registry.create_source(data)
    await registry.delete_source("my-stream")

    with pytest.raises(SourceNotFoundError):
        await registry.get_source("my-stream")


@pytest.mark.asyncio
async def test_delete_preloaded_source_raises(registry):
    """delete_source raises ValueError for pre-loaded streaming sources."""
    with pytest.raises(ValueError, match="cannot delete"):
        await registry.delete_source("espn")


@pytest.mark.asyncio
async def test_list_sources_includes_custom(registry):
    """list_sources includes newly created custom sources."""
    data = SourceCreate(name="Peacock", type="url", url="https://peacocktv.com")
    await registry.create_source(data)
    sources = await registry.list_sources()
    ids = {s.id for s in sources}
    assert "peacock" in ids
