"""Unit tests for parser."""

import pytest

from crawler.parser import BookParser, CatalogPageSummary
from crawler.models import Rating
from utils.validators import extract_price, sanitize_html


@pytest.fixture
def parser():
    return BookParser(base_url="https://books.toscrape.com")


def test_parse_catalog_page(parser, sample_catalog_html):
    summary = parser.parse_catalog_page(
        sample_catalog_html,
        page_url="https://books.toscrape.com/catalogue/page-1.html"
    )
    assert isinstance(summary, CatalogPageSummary)
    assert summary.has_next is True
    assert summary.current_page == 1
    assert summary.total_pages == 3
    assert len(summary.book_urls) == 1
    assert summary.book_urls[0].startswith("https://books.toscrape.com/catalogue/")


def test_parse_book_page(parser, sample_book_html):
    book = parser.parse_book_page(sample_book_html, "https://books.toscrape.com/book_1/index.html")
    assert book.name == "Book One"
    assert book.category == "Travel"
    assert book.price_incl_tax == pytest.approx(10.0)
    assert book.price_excl_tax == pytest.approx(8.0)
    assert book.num_reviews == 3
    assert book.rating == Rating.FOUR
    assert book.availability.startswith("In stock")
    assert book.content_hash


def test_parse_book_page_missing_fields(parser):
    html = "<html><body><div class='product_main'><h1>Untitled</h1></div></body></html>"
    with pytest.raises(Exception):
        parser.parse_book_page(html, "https://books.toscrape.com/missing")


def test_extract_price():
    assert extract_price("£51.77") == 51.77
    assert extract_price("$10.00") == 10.0
    assert extract_price("") == 0.0


def test_sanitize_html_truncates_long_payload():
    html = "<p>" + "a" * 120000 + "</p>"
    sanitized = sanitize_html(html, max_length=1000)
    assert sanitized.endswith("... [truncated]")
