"""Integration tests for FastAPI endpoints."""

import pytest
from fastapi import HTTPException

from datetime import datetime, timezone
from bson import ObjectId

from database.repositories.book_repository import BookRepository
from database.repositories.change_repository import ChangeRepository


@pytest.mark.asyncio
async def test_books_endpoint_returns_data(test_db, api_client):
    repo = BookRepository(test_db)
    book_doc = {
        "name": "Seed Book",
        "description": "desc",
        "category": "Fiction",
        "price_excl_tax": 8.0,
        "price_incl_tax": 10.0,
        "availability": "In stock",
        "num_reviews": 1,
        "image_url": "https://example.com/img.jpg",
        "rating": "Four",
        "source_url": "https://example.com/seed",
        "crawl_timestamp": datetime.now(timezone.utc),
        "status": "active",
        "content_hash": "hash",
        "raw_html": "<html></html>",
    }
    result = await repo.collection.insert_one(book_doc)

    response = await api_client.get("/books?limit=5")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["name"] == "Seed Book"

    detail = await api_client.get(f"/books/{result.inserted_id}")
    assert detail.status_code == 200


@pytest.mark.asyncio
async def test_changes_endpoint_filters(test_db, api_client):
    repo = ChangeRepository(test_db)
    await repo.collection.insert_one(
        {
            "book_id": ObjectId(),
            "book_name": "Seed Book",
            "change_type": "price_change",
            "field_name": "price_incl_tax",
            "old_value": "10.00",
            "new_value": "12.00",
            "detected_at": datetime.now(timezone.utc),
        }
    )

    response = await api_client.get("/changes?change_type=price_change")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["change_type"] == "price_change"


@pytest.mark.asyncio
async def test_rate_limit_enforced():
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    from api.middleware import RateLimitMiddleware
    from config.settings import settings
    from httpx import AsyncClient

    app = FastAPI()

    @app.get("/books")
    async def _handler():
        return JSONResponse({"ok": True})

    settings.api.api_keys = ["test-key"]
    app.add_middleware(RateLimitMiddleware, requests_per_hour=1)

    async with AsyncClient(app=app, base_url="http://test", headers={"X-API-Key": "test-key"}) as client:
        await client.get("/books")
        with pytest.raises(HTTPException) as exc:
            await client.get("/books")
        assert exc.value.status_code == 429

