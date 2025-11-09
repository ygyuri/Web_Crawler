"""API request and response schemas."""

from datetime import datetime
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field, HttpUrl, ConfigDict

from crawler.models import Rating

T = TypeVar("T")


class BookResponse(BaseModel):
    """Public book response model (excludes raw_html)."""

    id: str = Field(..., description="Book ID")
    name: str = Field(..., description="Book title")
    description: Optional[str] = Field(None, description="Book description")
    category: str = Field(..., description="Book category")
    price_excl_tax: float = Field(..., description="Price excluding tax")
    price_incl_tax: float = Field(..., description="Price including tax")
    availability: str = Field(..., description="Availability status")
    num_reviews: int = Field(..., description="Number of reviews")
    image_url: HttpUrl = Field(..., description="Book cover image URL")
    rating: Rating = Field(..., description="Book rating")
    source_url: HttpUrl = Field(..., description="Source URL")
    crawl_timestamp: datetime = Field(..., description="Crawl timestamp")

    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            HttpUrl: str,
        }
    )


class BookDetailResponse(BookResponse):
    """Detailed book response including raw_html."""

    raw_html: Optional[str] = Field(None, description="Raw HTML snapshot")


class ChangeResponse(BaseModel):
    """Change log entry response."""

    id: str = Field(..., description="Change ID")
    book_id: str = Field(..., description="Book ID")
    book_name: str = Field(..., description="Book name")
    change_type: str = Field(..., description="Type of change")
    field_name: Optional[str] = Field(None, description="Changed field name")
    old_value: Optional[str] = Field(None, description="Old value")
    new_value: Optional[str] = Field(None, description="New value")
    detected_at: datetime = Field(..., description="Detection timestamp")

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""

    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    pages: int = Field(..., ge=1, description="Total number of pages")
    limit: int = Field(..., ge=1, description="Items per page")

    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        limit: int
    ) -> "PaginatedResponse[T]":
        """
        Create paginated response.

        Args:
            items: List of items for current page
            total: Total number of items
            page: Current page number
            limit: Items per page

        Returns:
            PaginatedResponse instance
        """
        pages = (total + limit - 1) // limit if total > 0 else 1
        return cls(
            items=items,
            total=total,
            page=page,
            pages=pages,
            limit=limit
        )


class ErrorResponse(BaseModel):
    """Standardized error response."""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Error details")
    status_code: int = Field(..., description="HTTP status code")

