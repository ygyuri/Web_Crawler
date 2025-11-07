"""Change repository for change log operations."""

from datetime import datetime
from typing import List, Optional

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
                detected_at=datetime.utcnow()
            )

            result = await self.collection.insert_one(change_doc.model_dump(by_alias=True))
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
        limit: int = 50
    ) -> List[ChangeDocument]:
        """
        Get recent changes.

        Args:
            since: Filter changes since this datetime
            limit: Maximum number of changes to return

        Returns:
            List of ChangeDocument instances
        """
        try:
            filters = {}
            if since:
                filters["detected_at"] = {"$gte": since}

            cursor = self.collection.find(filters).sort("detected_at", -1).limit(limit)

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

