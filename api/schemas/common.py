"""Common API schemas for filtering and pagination."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from crawler.models import Rating


class SortBy(str, Enum):
    """Sort options for books."""

    RATING = "rating"
    PRICE = "price"
    REVIEWS = "reviews"
    NAME = "name"


class BookFilters(BaseModel):
    """Query filters for books endpoint."""

    category: Optional[str] = Field(None, description="Filter by category")
    min_price: Optional[float] = Field(None, ge=0, description="Minimum price")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price")
    rating: Optional[Rating] = Field(None, description="Filter by rating")
    sort_by: Optional[SortBy] = Field(
        default=SortBy.NAME,
        description="Sort field"
    )
    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")

    @field_validator("max_price")
    @classmethod
    def validate_price_range(cls, v: Optional[float], info) -> Optional[float]:
        """Ensure max_price >= min_price."""
        if v is not None and "min_price" in info.data:
            min_price = info.data["min_price"]
            if min_price is not None and v < min_price:
                raise ValueError("max_price must be >= min_price")
        return v


class ChangeFilters(BaseModel):
    """Query filters for changes endpoint."""

    since: Optional[datetime] = Field(
        None,
        description="Filter changes since this datetime"
    )
    change_type: Optional[str] = Field(
        None,
        description="Filter by change type (new, price_change, availability_change)"
    )
    limit: int = Field(default=50, ge=1, le=100, description="Items per page")
    page: int = Field(default=1, ge=1, description="Page number")

