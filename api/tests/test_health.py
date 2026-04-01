"""Health check endpoint tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Health endpoint should return 200 with status."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "services" in data


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Root endpoint should return API info."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "MedBed Insight API"
    assert "version" in data
