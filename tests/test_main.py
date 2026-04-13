"""Tests for the FastAPI application entry point."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """GET /api/v1/server/health returns 200 with status ok."""
    response = await client.get("/api/v1/server/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
