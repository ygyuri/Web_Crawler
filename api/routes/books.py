"""Book API endpoints."""

from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.auth import verify_api_key
from api.dependencies import get_book_repository
from api.schemas.books import BookResponse, BookDetailResponse, PaginatedResponse
from api.schemas.common import BookFilters, SortBy
from crawler.models import Rating
from database.repositories.book_repository import BookRepository

router = APIRouter(prefix="/books", tags=["books"])


@router.get("", response_model=PaginatedResponse[BookResponse])
async def get_books(
    category: Optional[str] = Query(None, description="Filter by category"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    rating: Optional[str] = Query(None, description="Filter by rating"),
    sort_by: Optional[str] = Query("name", description="Sort field"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
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
    # Build filters
    filters = {"status": "active"}

    if category:
        filters["category"] = category

    if min_price is not None or max_price is not None:
        price_filter = {}
        if min_price is not None:
            price_filter["$gte"] = min_price
        if max_price is not None:
            price_filter["$lte"] = max_price
        filters["price_incl_tax"] = price_filter

    if rating:
        try:
            rating_enum = Rating(rating)
            filters["rating"] = rating_enum.value
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid rating: {rating}"
            )

    # Build sort
    sort_mapping = {
        "name": [("name", 1)],
        "price": [("price_incl_tax", 1)],
        "rating": [("rating", -1)],
        "reviews": [("num_reviews", -1)]
    }
    sort = sort_mapping.get(sort_by, [("name", 1)])

    # Calculate skip
    skip = (page - 1) * limit

    # Fetch books
    books = await book_repo.find_books(filters, skip=skip, limit=limit, sort=sort)
    total = await book_repo.count_books(filters)

    # Convert to response models
    book_responses = []
    for book in books:
        # Get book ID from database
        book_doc = await book_repo.collection.find_one({"source_url": str(book.source_url)})
        book_id = str(book_doc["_id"]) if book_doc else str(book.source_url)

        book_responses.append(
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
        )

    return PaginatedResponse.create(book_responses, total, page, limit)


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
    # Try to get by ID first, then by URL
    book = await book_repo.get_book_by_id(book_id)
    if not book:
        book = await book_repo.get_book_by_url(book_id)

    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book not found: {book_id}"
        )

    return BookDetailResponse(
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
        crawl_timestamp=book.crawl_timestamp,
        raw_html=book.raw_html
    )

