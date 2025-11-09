"""Unit tests for hashing utilities."""

from crawler.models import Book, Rating
from utils.hashing import generate_content_hash, hash_dict


def _make_book(**overrides):
    base = dict(
        name="Book",
        category="Fiction",
        price_excl_tax=10.0,
        price_incl_tax=12.0,
        availability="In stock",
        num_reviews=1,
        image_url="https://example.com/image.jpg",
        rating=Rating.THREE,
        source_url="https://example.com/book",
        content_hash="placeholder",
    )
    base.update(overrides)
    book = Book(**base)
    book.content_hash = "placeholder"
    return book


def test_generate_content_hash_stable():
    book = _make_book()
    hash_one = generate_content_hash(book)
    hash_two = generate_content_hash(book)
    assert hash_one == hash_two


def test_generate_content_hash_changes_on_update():
    book = _make_book()
    hash_one = generate_content_hash(book)
    book.price_incl_tax = 15.0
    hash_two = generate_content_hash(book)
    assert hash_one != hash_two


def test_hash_dict_is_deterministic():
    data = {"a": 1, "b": 2}
    assert hash_dict(data) == hash_dict({"b": 2, "a": 1})



