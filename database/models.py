"""MongoDB document models and collections."""

from datetime import datetime
from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, Field


class BookDocument(BaseModel):
    """MongoDB book document model."""

    _id: Optional[ObjectId] = Field(None, alias="_id")
    name: str
    description: Optional[str] = None
    category: str
    price_excl_tax: float
    price_incl_tax: float
    availability: str
    num_reviews: int = 0
    image_url: str
    rating: str
    source_url: str
    crawl_timestamp: datetime
    status: str = "active"
    content_hash: str
    raw_html: Optional[str] = None

    class Config:
        """Pydantic configuration."""

        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat(),
        }


class ChangeDocument(BaseModel):
    """MongoDB change log document model."""

    _id: Optional[ObjectId] = Field(None, alias="_id")
    book_id: ObjectId
    book_name: str
    change_type: str  # "new", "price_change", "availability_change", etc.
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    detected_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic configuration."""

        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat(),
        }


class CrawlerStateDocument(BaseModel):
    """MongoDB crawler state document model."""

    _id: Optional[ObjectId] = Field(None, alias="_id")
    last_page: int = 1
    last_run: datetime = Field(default_factory=datetime.utcnow)
    status: str = "idle"  # "idle", "running", "error"
    total_books_crawled: int = 0
    error_message: Optional[str] = None

    class Config:
        """Pydantic configuration."""

        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat(),
        }

