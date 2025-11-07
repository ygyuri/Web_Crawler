"""Pytest configuration and fixtures."""

import pytest
from motor.motor_asyncio import AsyncIOMotorClient

from database.connection import Database


@pytest.fixture
async def test_db():
    """Create test database."""
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.test_books_crawler
    yield db
    await client.drop_database("test_books_crawler")
    client.close()


@pytest.fixture
async def mock_http_client():
    """Mock HTTP client for testing."""
    # TODO: Implement httpx mock transport
    pass

