"""Unit tests for parser."""

import pytest
from crawler.parser import BookParser


def test_parse_book_urls():
    """Test parsing book URLs from catalog page."""
    parser = BookParser()
    html = '<article class="product_pod"><h3><a href="/catalogue/book.html">Book</a></h3></article>'
    urls = parser.parse_book_urls(html)
    assert len(urls) > 0


def test_extract_price():
    """Test price extraction."""
    from utils.validators import extract_price
    assert extract_price("£51.77") == 51.77
    assert extract_price("$10.00") == 10.0

