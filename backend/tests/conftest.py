"""
Pytest fixtures for GovAI backend tests.
"""

import os
import sys
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport

# Ensure backend is in path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment variables before importing app
os.environ.setdefault("GOVAI_API_KEY", "test-api-key-for-testing")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")


@pytest.fixture
def valid_api_key():
    """Return the valid API key for testing."""
    return os.environ.get("GOVAI_API_KEY", "test-api-key-for-testing")


@pytest.fixture
def valid_headers(valid_api_key):
    """Return headers with valid API key."""
    return {"X-GovAI-Key": valid_api_key}


@pytest.fixture
def invalid_headers():
    """Return headers with invalid API key."""
    return {"X-GovAI-Key": "invalid-key-12345"}


@pytest.fixture
async def client():
    """Create an async test client for the FastAPI app."""
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
