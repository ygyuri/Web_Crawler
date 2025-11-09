"""Book API endpoints."""

from typing import Dict, List, Tuple, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from api.auth import verify_api_key
from api.dependencies import get_book_repository
from api.schemas.books import BookResponse, BookDetailResponse, PaginatedResponse
from api.schemas.common import BookFilters, SortBy
from database.repositories.book_repository import BookRepository

router = APIRouter(prefix="/books", tags=["books"])


@router.get("", response_model=PaginatedResponse[BookResponse])
async def get_books(
    filters: BookFilters = Depends(),
    api_key: str = Depends(verify_api_key),
    book_repo: BookRepository = Depends(get_book_repository)
):
    """
    Get paginated list of books with filtering and sorting.

    Args:
        category: Filter by category
        min_price: Minimum price filter
        max_price: Maximum price filter
        rating: Filter by rating
        sort_by: Sort field (name, price, rating, reviews)
        page: Page number
        limit: Items per page
        api_key: API key (from dependency)
        book_repo: Book repository (from dependency)

    Returns:
        Paginated list of books
    """
    # Build Mongo filters
    query_filters: Dict = {"status": "active"}
    if filters.category:
        query_filters["category"] = filters.category

    if filters.min_price is not None or filters.max_price is not None:
        price_filter: Dict[str, float] = {}
        if filters.min_price is not None:
            price_filter["$gte"] = filters.min_price
        if filters.max_price is not None:
            price_filter["$lte"] = filters.max_price
        query_filters["price_incl_tax"] = price_filter

    if filters.rating is not None:
        query_filters["rating"] = filters.rating.value

    sort_mapping = {
        SortBy.NAME: [("name", 1)],
        SortBy.PRICE: [("price_incl_tax", 1)],
        SortBy.RATING: [("rating", -1)],
        SortBy.REVIEWS: [("num_reviews", -1)],
    }
    sort = sort_mapping.get(filters.sort_by, [("name", 1)])

    skip = (filters.page - 1) * filters.limit

    items_with_ids = await book_repo.find_books_with_ids(
        query_filters,
        skip=skip,
        limit=filters.limit,
        sort=sort
    )
    total = await book_repo.count_books(query_filters)

    book_responses: List[BookResponse] = [
        BookResponse(
            id=book_id,
            name=book.name,
            description=book.description,
            category=book.category,
            price_excl_tax=book.price_excl_tax,
            price_incl_tax=book.price_incl_tax,
            availability=book.availability,
            num_reviews=book.num_reviews,
            image_url=book.image_url,
            rating=book.rating,
            source_url=book.source_url,
            crawl_timestamp=book.crawl_timestamp
        )
        for book_id, book in items_with_ids
    ]

    return PaginatedResponse.create(
        book_responses,
        total,
        filters.page,
        filters.limit
    )


@router.get("/{book_id}", response_model=BookDetailResponse)
async def get_book(
    book_id: str,
    api_key: str = Depends(verify_api_key),
    book_repo: BookRepository = Depends(get_book_repository)
):
    """
    Get book details by ID.

    Args:
        book_id: Book ID (MongoDB ObjectId or source URL)
        api_key: API key (from dependency)
        book_repo: Book repository (from dependency)

    Returns:
        Book details including raw HTML
    """
    doc = None
    canonical_id = None

    # Try lookup by ObjectId
    try:
        doc = await book_repo.collection.find_one({"_id": ObjectId(book_id)})
        if doc:
            canonical_id = str(doc["_id"])
    except Exception:
        doc = None

    # Fallback lookup by source_url
    if not doc:
        doc = await book_repo.collection.find_one({"source_url": book_id})
        if doc:
            canonical_id = str(doc["_id"])

    if not doc or canonical_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book not found: {book_id}"
        )

    book = book_repo._document_to_book(doc)

    return BookDetailResponse(
        id=canonical_id,
        name=book.name,
        description=book.description,
        category=book.category,
        price_excl_tax=book.price_excl_tax,
        price_incl_tax=book.price_incl_tax,
        availability=book.availability,
        num_reviews=book.num_reviews,
        image_url=book.image_url,
        rating=book.rating,
        source_url=book.source_url,
        crawl_timestamp=book.crawl_timestamp,
        raw_html=book.raw_html
    )

