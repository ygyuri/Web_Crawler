"""Unit tests for utility helpers."""

from utils.validators import extract_number, normalize_url, sanitize_html


def test_normalize_url_absolute():
    assert normalize_url("https://example.com/page", "https://base.com") == "https://example.com/page"


def test_normalize_url_relative():
    assert normalize_url("/page", "https://example.com") == "https://example.com/page"


def test_extract_number():
    assert extract_number("In stock (22 available)") == 22
    assert extract_number("No numbers here") == 0


def test_sanitize_html_empty():
    assert sanitize_html("") == ""



