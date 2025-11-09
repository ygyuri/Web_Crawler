"""Crawler state repository for state management."""

from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from config.logging_config import get_logger
from crawler.models import CrawlerState
from database.models import CrawlerStateDocument

logger = get_logger(__name__)


class StateRepository:
    """Repository for crawler state operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize state repository.

        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.collection = db.crawler_state

    async def save_state(self, state: CrawlerState) -> bool:
        """
        Save crawler state (upsert).

        Args:
            state: CrawlerState model instance

        Returns:
            True if successful
        """
        try:
            state_dict = state.model_dump()
            await self.collection.update_one(
                {"_id": "crawler_state"},
                {"$set": state_dict},
                upsert=True
            )
            logger.debug(f"Saved crawler state: page {state.last_page}")
            return True
        except Exception as e:
            logger.error(f"Failed to save state: {e}", exc_info=True)
            raise

    async def get_last_state(self) -> Optional[CrawlerState]:
        """
        Get last crawler state.

        Returns:
            CrawlerState model or None if not found
        """
        try:
            doc = await self.collection.find_one({"_id": "crawler_state"})
            if doc:
                return CrawlerState(**doc)
            return None
        except Exception as e:
            logger.error(f"Failed to get last state: {e}", exc_info=True)
            raise

    async def update_last_page(self, page: int) -> bool:
        """
        Update last crawled page number.

        Args:
            page: Page number

        Returns:
            True if updated
        """
        try:
            result = await self.collection.update_one(
                {"_id": "crawler_state"},
                {
                    "$set": {
                        "last_page": page,
                        "last_run": datetime.now(timezone.utc)
                    }
                },
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error(f"Failed to update last page: {e}", exc_info=True)
            raise

    async def clear_state(self) -> None:
        """Delete persisted crawler state."""
        try:
            await self.collection.delete_one({"_id": "crawler_state"})
            logger.debug("Cleared crawler state")
        except Exception as e:
            logger.error(f"Failed to clear state: {e}", exc_info=True)
            raise

