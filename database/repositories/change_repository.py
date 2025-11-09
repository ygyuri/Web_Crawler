"""Change repository for change log operations."""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from config.logging_config import get_logger
from database.models import ChangeDocument

logger = get_logger(__name__)


class ChangeRepository:
    """Repository for change log operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize change repository.

        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.collection = db.changes

    async def log_change(
        self,
        book_id: str,
        book_name: str,
        change_type: str,
        field_name: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None
    ) -> str:
        """
        Log a change to the database.

        Args:
            book_id: Book ID
            book_name: Book name
            change_type: Type of change (new, price_change, etc.)
            field_name: Name of changed field
            old_value: Old value
            new_value: New value

        Returns:
            Change log entry ID
        """
        try:
            change_doc = ChangeDocument(
                book_id=ObjectId(book_id),
                book_name=book_name,
                change_type=change_type,
                field_name=field_name,
                old_value=str(old_value) if old_value is not None else None,
                new_value=str(new_value) if new_value is not None else None,
                detected_at=datetime.now(timezone.utc)
            )

            payload = change_doc.model_dump(by_alias=True, exclude_none=True)
            result = await self.collection.insert_one(payload)
            change_id = str(result.inserted_id)

            logger.info(
                f"Logged change: {change_type} for book {book_name}",
                extra={"change_id": change_id, "book_id": book_id}
            )
            return change_id
        except Exception as e:
            logger.error(f"Failed to log change: {e}", exc_info=True)
            raise

    async def get_recent_changes(
        self,
        since: Optional[datetime] = None,
        change_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[ChangeDocument]:
        """
        Get recent changes.

        Args:
            since: Filter changes since this datetime
            change_type: Filter by change type
            skip: Number of documents to skip
            limit: Maximum number of changes to return

        Returns:
            List of ChangeDocument instances
        """
        try:
            filters: Dict = {}
            if since:
                filters["detected_at"] = {"$gte": since}
            if change_type:
                filters["change_type"] = change_type

            cursor = (
                self.collection.find(filters)
                .sort("detected_at", -1)
                .skip(skip)
                .limit(limit)
            )

            changes = []
            async for doc in cursor:
                changes.append(ChangeDocument(**doc))
            return changes
        except Exception as e:
            logger.error(f"Failed to get recent changes: {e}", exc_info=True)
            raise

    async def get_changes_by_book(self, book_id: str) -> List[ChangeDocument]:
        """
        Get all changes for a specific book.

        Args:
            book_id: Book ID

        Returns:
            List of ChangeDocument instances
        """
        try:
            cursor = self.collection.find({"book_id": ObjectId(book_id)}).sort(
                "detected_at",
                -1
            )

            changes = []
            async for doc in cursor:
                changes.append(ChangeDocument(**doc))
            return changes
        except Exception as e:
            logger.error(f"Failed to get changes by book: {e}", exc_info=True)
            raise

    async def count_recent_changes(
        self,
        since: Optional[datetime] = None,
        change_type: Optional[str] = None
    ) -> int:
        """
        Count changes matching filters.

        Args:
            since: Filter changes since this datetime
            change_type: Filter by change type

        Returns:
            Count of matching change documents.
        """
        try:
            filters: Dict = {}
            if since:
                filters["detected_at"] = {"$gte": since}
            if change_type:
                filters["change_type"] = change_type
            return await self.collection.count_documents(filters)
        except Exception as exc:
            logger.error(
                "Failed to count recent changes",
                extra={"error": str(exc)},
                exc_info=True
            )
            raise

