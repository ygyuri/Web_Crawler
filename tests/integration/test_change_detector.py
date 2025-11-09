"""Integration tests for change detector."""

from datetime import datetime

import pytest

from scheduler.change_detector import ChangeDetector
from database.repositories.book_repository import BookRepository
from utils.hashing import generate_content_hash
from crawler.models import Book, Rating


def _existing_book() -> Book:
    book = Book(
        name="Book One",
        description="Test book description.",
        category="Travel",
        price_excl_tax=8.0,
        price_incl_tax=10.0,
        availability="In stock (5 available)",
        num_reviews=3,
        image_url="https://books.toscrape.com/media/cache/book_1.jpg",
        rating=Rating.FOUR,
        source_url="https://books.toscrape.com/catalogue/book_1/index.html",
        raw_html="<html></html>",
        content_hash="placeholder",
    )
    book.content_hash = generate_content_hash(book)
    return book


@pytest.mark.asyncio
async def test_change_detector_identifies_price_change(
    test_db,
    respx_mock,
    sample_catalog_html,
    sample_book_html,
    monkeypatch,
):
    repo = BookRepository(test_db)
    existing = _existing_book()
    await repo.upsert_book(existing)

    respx_mock.get(url__regex=r"https://books\.toscrape\.com/+catalogue/page-1\.html").respond(200, text=sample_catalog_html)
    updated_html = sample_book_html.replace("£10.00", "£12.00").replace("£8.00", "£9.50")
    respx_mock.get(url__regex=r"https://books\.toscrape\.com/+catalogue/book_1/index\.html").respond(200, text=updated_html)
    respx_mock.get(url__regex=r"https://books\.toscrape\.com/+catalogue/page-2\.html").respond(404)

    detector = ChangeDetector()
    stats = await detector.detect_changes()

    assert stats["changed_books"] == 1
    assert stats["price_changes"] >= 1

