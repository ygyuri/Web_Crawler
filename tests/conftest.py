"""Pytest configuration and fixtures."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Dict, Tuple
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from respx import MockRouter

from api.main import app as fastapi_app
from config.settings import settings
from database.connection import Database

FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@asynccontextmanager
async def _test_db_context() -> AsyncIterator[AsyncIOMotorDatabase]:
    """Internal helper to create and cleanup a test database."""
    client = AsyncIOMotorClient(settings.database.url)
    db_name = f"test_books_crawler_{uuid4().hex}"
    db = client[db_name]
    try:
        yield db
    finally:
        await client.drop_database(db_name)
        client.close()


@pytest.fixture
async def test_db(monkeypatch) -> AsyncIterator[AsyncIOMotorDatabase]:
    """
    Provide an isolated MongoDB database for tests.

    Ensures Database.connect/disconnect use the temporary database.
    """
    async with _test_db_context() as db:
        client = db.client

        async def _connect() -> None:
            Database.client = client
            Database.database = db

        async def _disconnect() -> None:
            Database.client = None
            Database.database = None

        await _connect()
        monkeypatch.setattr(Database, "connect", _connect)
        monkeypatch.setattr(Database, "disconnect", _disconnect)
        yield db
        await _disconnect()


@pytest.fixture
def respx_mock():
    """Provide a respx mock router."""
    with MockRouter(assert_all_called=False) as router:
        yield router


@pytest.fixture
def sample_catalog_html() -> str:
    """Return sample catalog HTML."""
    return (FIXTURE_DIR / "catalog_page.html").read_text()


@pytest.fixture
def sample_book_html() -> str:
    """Return sample book detail HTML."""
    return (FIXTURE_DIR / "book_page.html").read_text()


@pytest.fixture
def sample_change() -> Dict[str, str]:
    """Sample change log entry data."""
    return {
        "book_id": uuid4().hex,
        "book_name": "Test Book",
        "change_type": "price_change",
        "field_name": "price_incl_tax",
        "old_value": "10.00",
        "new_value": "12.00",
    }


@pytest.fixture
def api_app(test_db, monkeypatch) -> FastAPI:
    """Return the FastAPI app with test configuration."""
    monkeypatch.setattr(settings.api, "api_keys", ["test-key"])
    return fastapi_app


@pytest.fixture
async def api_client(api_app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Provide an HTTPX async client for the FastAPI app."""
    async with AsyncClient(app=api_app, base_url="http://test", headers={"X-API-Key": "test-key"}) as client:
        client._app = api_app  # type: ignore[attr-defined]
        yield client


@pytest.fixture
def pagination_params() -> Tuple[int, int]:
    """Default pagination parameters for tests."""
    return 1, 20

