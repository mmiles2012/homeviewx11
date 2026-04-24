"""Shared test fixtures for HomeView server tests."""

import pytest
from httpx import AsyncClient, ASGITransport

from server.main import app


@pytest.fixture
async def client() -> AsyncClient:
    """Async HTTP client bound to the FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
