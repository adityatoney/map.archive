"""Test configuration and fixtures."""

import asyncio
import os
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Set test environment before importing app
os.environ["DATABASE_URL"] = "postgresql+asyncpg://medbed:medbed@localhost:5432/medbed_test"
os.environ["DATABASE_URL_SYNC"] = "postgresql://medbed:medbed@localhost:5432/medbed_test"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["ENCRYPTION_KEY"] = "dGVzdC1lbmNyeXB0aW9uLWtleS1mb3ItdGVzdGluZw=="
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["UMLS_API_KEY"] = "mock"
os.environ["ANTHROPIC_API_KEY"] = "mock"
os.environ["NEO4J_ENABLED"] = "false"
os.environ["ENVIRONMENT"] = "testing"

from app.main import create_app


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def app():
    """Create a test FastAPI application."""
    return create_app()


@pytest_asyncio.fixture
async def client(app):
    """Create an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def auth_headers():
    """Generate auth headers with a test JWT token."""
    from app.utils.auth import create_access_token

    token = create_access_token(data={"sub": "demo@medbed.local"})
    return {"Authorization": f"Bearer {token}"}
