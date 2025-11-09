"""Crawler state management."""

from datetime import datetime, timezone
from typing import Optional

from config.logging_config import get_logger
from crawler.models import CrawlerState
from database.connection import Database
from database.repositories.state_repository import StateRepository

logger = get_logger(__name__)


class StateManager:
    """Manages crawler state for resumption."""

    def __init__(self):
        """Initialize state manager."""
        self.repository: Optional[StateRepository] = None

    async def initialize(self) -> None:
        """Initialize state repository."""
        db = Database.get_database()
        self.repository = StateRepository(db)

    async def get_last_state(self) -> CrawlerState:
        """
        Get last crawler state or create default.

        Returns:
            CrawlerState instance
        """
        if not self.repository:
            await self.initialize()

        state = await self.repository.get_last_state()
        if state:
            return state

        # Return default state
        return CrawlerState()

    async def save_state(
        self,
        last_page: int,
        total_books: int,
        status: str = "running"
    ) -> None:
        """
        Save crawler state.

        Args:
            last_page: Last crawled page number
            total_books: Total books crawled
            status: Crawler status
        """
        if not self.repository:
            await self.initialize()

        state = CrawlerState(
            last_page=last_page,
            last_run=datetime.now(timezone.utc),
            status=status,
            total_books_crawled=total_books
        )
        await self.repository.save_state(state)
        logger.info(
            f"Saved crawler state: page {last_page}, books {total_books}, status {status}"
        )

    async def update_page(self, page: int) -> None:
        """
        Update last crawled page.

        Args:
            page: Page number
        """
        if not self.repository:
            await self.initialize()

        await self.repository.update_last_page(page)

    async def reset(self) -> None:
        """Clear persisted crawler state."""
        if not self.repository:
            await self.initialize()
        await self.repository.clear_state()

