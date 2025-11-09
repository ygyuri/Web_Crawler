"""Unit tests for models."""

import pytest
from crawler.models import Book, Rating


def test_rating_enum():
    """Test Rating enum."""
    assert Rating.ONE.value == "One"
    assert Rating.FIVE.to_int() == 5


def test_book_model():
    """Test Book model validation."""
    book = Book(
        name="Test Book",
        category=" Fiction ",
        price_excl_tax=10.0,
        price_incl_tax=12.0,
        availability=" In stock ",
        num_reviews=5,
        image_url="https://example.com/image.jpg",
        rating=Rating.FIVE,
        source_url="https://example.com/book",
        content_hash="test_hash",
        raw_html="<html></html>"
    )
    assert book.name == "Test Book"
    assert book.rating == Rating.FIVE
    assert book.category == "Fiction"
    assert book.availability == "In stock"


def test_book_model_price_validation():
    with pytest.raises(ValueError):
        Book(
            name="Invalid Book",
            category="Fiction",
            price_excl_tax=15.0,
            price_incl_tax=10.0,
            availability="In stock",
            image_url="https://example.com/image.jpg",
            rating=Rating.THREE,
            source_url="https://example.com/book",
            content_hash="hash"
        )


def test_book_model_invalid_url():
    with pytest.raises(ValueError):
        Book(
            name="Invalid URL",
            category="Fiction",
            price_excl_tax=10.0,
            price_incl_tax=12.0,
            availability="In stock",
            image_url="not-a-url",
            rating=Rating.TWO,
            source_url="https://example.com/book",
            content_hash="hash"
        )

