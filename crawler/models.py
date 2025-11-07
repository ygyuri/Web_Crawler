"""Pydantic models for book data and crawler state."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


class Rating(str, Enum):
    """Book rating enumeration."""

    ONE = "One"
    TWO = "Two"
    THREE = "Three"
    FOUR = "Four"
    FIVE = "Five"

    @classmethod
    def from_star_class(cls, star_class: str) -> "Rating":
        """
        Convert star-rating CSS class to Rating enum.

        Args:
            star_class: CSS class like "star-rating One"

        Returns:
            Rating enum value
        """
        for rating in cls:
            if rating.value in star_class:
                return rating
        return cls.ONE  # Default to ONE if not found

    def to_int(self) -> int:
        """Convert rating to integer (1-5)."""
        mapping = {
            self.ONE: 1,
            self.TWO: 2,
            self.THREE: 3,
            self.FOUR: 4,
            self.FIVE: 5,
        }
        return mapping[self]


class Book(BaseModel):
    """Book data model with validation."""

    # Core book data
    name: str = Field(..., description="Book title")
    description: Optional[str] = Field(None, description="Book description")
    category: str = Field(..., description="Book category")
    price_excl_tax: float = Field(..., ge=0, description="Price excluding tax")
    price_incl_tax: float = Field(..., ge=0, description="Price including tax")
    availability: str = Field(..., description="Availability status")
    num_reviews: int = Field(default=0, ge=0, description="Number of reviews")
    image_url: HttpUrl = Field(..., description="Book cover image URL")
    rating: Rating = Field(..., description="Book rating")

    # Metadata
    source_url: HttpUrl = Field(..., description="Source URL of the book page")
    crawl_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when book was crawled"
    )
    status: str = Field(
        default="active",
        description="Book status (active, inactive, deleted)"
    )
    content_hash: str = Field(
        ...,
        description="Content hash for change detection"
    )

    # Raw data fallback
    raw_html: Optional[str] = Field(
        None,
        description="Raw HTML snapshot of the book page"
    )

    @field_validator("price_incl_tax")
    @classmethod
    def validate_price_incl_tax(cls, v: float, info) -> float:
        """Ensure price including tax is >= price excluding tax."""
        if "price_excl_tax" in info.data and v < info.data["price_excl_tax"]:
            raise ValueError(
                "Price including tax must be >= price excluding tax"
            )
        return v

    @field_validator("availability")
    @classmethod
    def validate_availability(cls, v: str) -> str:
        """Normalize availability string."""
        return v.strip()

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Normalize category string."""
        return v.strip()

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: str,
        }


class CrawlerState(BaseModel):
    """Crawler state for resumption logic."""

    last_page: int = Field(
        default=1,
        ge=1,
        description="Last successfully crawled page number"
    )
    last_run: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of last crawl run"
    )
    status: str = Field(
        default="idle",
        description="Crawler status (idle, running, error)"
    )
    total_books_crawled: int = Field(
        default=0,
        ge=0,
        description="Total number of books crawled"
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message if status is 'error'"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

