"""Unit tests for models."""

import pytest
from crawler.models import Book, Rating


def test_rating_enum():
    """Test Rating enum."""
    assert Rating.ONE.value == "One"
    assert Rating.FIVE.value == "Five"


def test_book_model():
    """Test Book model validation."""
    book = Book(
        name="Test Book",
        category="Fiction",
        price_excl_tax=10.0,
        price_incl_tax=12.0,
        availability="In stock",
        image_url="https://example.com/image.jpg",
        rating=Rating.FIVE,
        source_url="https://example.com/book",
        content_hash="test_hash"
    )
    assert book.name == "Test Book"
    assert book.rating == Rating.FIVE

