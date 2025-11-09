"""Integration tests for repository layer."""

import pytest

from crawler.models import Book, Rating
from database.repositories.book_repository import BookRepository
from database.repositories.change_repository import ChangeRepository
from database.repositories.state_repository import StateRepository
from utils.hashing import generate_content_hash
from crawler.models import CrawlerState
from bson import ObjectId


def _build_book(**overrides) -> Book:
    data = dict(
        name="Integration Book",
        description="desc",
        category="Travel",
        price_excl_tax=10.0,
        price_incl_tax=12.0,
        availability="In stock",
        num_reviews=2,
        image_url="https://example.com/image.jpg",
        rating=Rating.FOUR,
        source_url="https://example.com/book",
        raw_html="<html></html>",
        content_hash="placeholder",
    )
    data.update(overrides)
    book = Book(**data)
    book.content_hash = generate_content_hash(book)
    return book


@pytest.mark.asyncio
async def test_book_repository_upsert_and_get(test_db):
    repo = BookRepository(test_db)
    book = _build_book()

    book_id = await repo.upsert_book(book)

    stored = await repo.get_book_by_id(book_id)
    assert stored is not None
    assert stored.name == book.name

    book.price_incl_tax = 14.0
    await repo.upsert_book(book)
    updated = await repo.get_book_by_url(str(book.source_url))
    assert updated.price_incl_tax == 14.0


@pytest.mark.asyncio
async def test_change_repository_log_and_fetch(test_db):
    repo = ChangeRepository(test_db)
    book_repo = BookRepository(test_db)
    book = _build_book(source_url="https://example.com/book-change")
    result = await book_repo.collection.insert_one(book.model_dump(mode="json"))
    book_id = str(result.inserted_id)

    change_id = await repo.log_change(
        book_id=book_id,
        book_name=book.name,
        change_type="price_change",
        field_name="price_incl_tax",
        old_value="10.00",
        new_value="12.00"
    )

    changes = await repo.get_recent_changes(limit=5)
    assert any(change.change_type == "price_change" for change in changes)


@pytest.mark.asyncio
async def test_state_repository_save_and_get(test_db):
    repo = StateRepository(test_db)
    state = CrawlerState(last_page=3, total_books_crawled=10, status="running")
    await repo.save_state(state)
    state = await repo.get_last_state()
    assert state
    assert state.last_page == 3
    await repo.update_last_page(5)
    updated = await repo.get_last_state()
    assert updated.last_page == 5

