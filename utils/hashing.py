"""Content hashing utilities for change detection."""

import hashlib
import json
from typing import Dict, Any

from crawler.models import Book


def generate_content_hash(book: Book) -> str:
    """
    Generate content hash for a book (for change detection).

    Hashes key fields: name, price_incl_tax, price_excl_tax, availability, rating.

    Args:
        book: Book model instance

    Returns:
        SHA256 hash string
    """
    # Create a dictionary of key fields for hashing
    hash_data = {
        "name": book.name,
        "price_incl_tax": book.price_incl_tax,
        "price_excl_tax": book.price_excl_tax,
        "availability": book.availability,
        "rating": book.rating.value if hasattr(book.rating, "value") else str(book.rating)
    }

    # Convert to JSON string and hash
    hash_string = json.dumps(hash_data, sort_keys=True)
    return hashlib.sha256(hash_string.encode("utf-8")).hexdigest()


def hash_dict(data: Dict[str, Any]) -> str:
    """
    Generate hash for a dictionary.

    Args:
        data: Dictionary to hash

    Returns:
        SHA256 hash string
    """
    hash_string = json.dumps(data, sort_keys=True)
    return hashlib.sha256(hash_string.encode("utf-8")).hexdigest()

