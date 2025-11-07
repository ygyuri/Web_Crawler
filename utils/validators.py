"""Custom validators for data validation."""

from typing import Any
from urllib.parse import urljoin, urlparse


def normalize_url(url: str, base_url: str) -> str:
    """
    Normalize a URL (convert relative to absolute).

    Args:
        url: URL to normalize
        base_url: Base URL for relative URLs

    Returns:
        Normalized absolute URL
    """
    if not url:
        return ""

    # If already absolute, return as is
    parsed = urlparse(url)
    if parsed.scheme:
        return url

    # Join with base URL
    return urljoin(base_url, url)


def sanitize_html(html: str, max_length: int = 100000) -> str:
    """
    Sanitize HTML content (truncate if too long).

    Args:
        html: HTML string
        max_length: Maximum length before truncation

    Returns:
        Sanitized HTML string
    """
    if not html:
        return ""

    if len(html) > max_length:
        return html[:max_length] + "... [truncated]"

    return html


def extract_price(price_string: str) -> float:
    """
    Extract numeric price from string (e.g., "£51.77" -> 51.77).

    Args:
        price_string: Price string

    Returns:
        Float price value
    """
    if not price_string:
        return 0.0

    # Remove currency symbols and whitespace
    cleaned = price_string.replace("£", "").replace("$", "").replace("€", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def extract_number(text: str) -> int:
    """
    Extract number from text (e.g., "In stock (22 available)" -> 22).

    Args:
        text: Text containing number

    Returns:
        Extracted integer or 0 if not found
    """
    if not text:
        return 0

    import re
    numbers = re.findall(r"\d+", text)
    if numbers:
        return int(numbers[0])
    return 0

