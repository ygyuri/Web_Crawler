"""Change detection algorithm for detecting book updates."""

import asyncio
from typing import Dict, List, Optional

from config.logging_config import get_logger, setup_logging
from crawler.models import Book
from crawler.scraper import BookScraper
from database.connection import Database
from database.repositories.book_repository import BookRepository
from database.repositories.change_repository import ChangeRepository
from utils.exceptions import HTTPClientError, ParsingError
from utils.validators import sanitize_html

logger = get_logger(__name__)


class ChangeDetector:
    """Detects changes in book data."""

    def __init__(self):
        """Initialize change detector."""
        self.book_repo: Optional[BookRepository] = None
        self.change_repo: Optional[ChangeRepository] = None
        self.scraper: Optional[BookScraper] = None

    async def initialize(self) -> None:
        """Initialize change detector."""
        await Database.connect()
        db = Database.get_database()

        self.book_repo = BookRepository(db)
        self.change_repo = ChangeRepository(db)
        self.scraper = BookScraper()
        await self.scraper.initialize()

        logger.info("Change detector initialized")

    async def close(self) -> None:
        """Close change detector resources."""
        if self.scraper:
            await self.scraper.close()
        await Database.disconnect()

    async def detect_changes(self) -> Dict[str, int]:
        """
        Detect changes by crawling and comparing with stored data.

        Returns:
            Dictionary with change statistics.
        """
        try:
            await self.initialize()

            if not self.scraper or not self.book_repo or not self.change_repo:
                raise RuntimeError("Change detector not properly initialized.")

            stats = self._empty_stats()
            logger.info("Starting change detection crawl")

            page = 1
            seen_urls = set()

            while True:
                catalog_url = f"{self.scraper.base_url}/catalogue/page-{page}.html"
                try:
                    html = await self.scraper.client.fetch_html(catalog_url)
                except HTTPClientError as exc:
                    logger.error(
                        "Failed to fetch catalog page during change detection",
                        extra={"page": page, "url": catalog_url, "error": str(exc)}
                    )
                    stats["errors"] += 1
                    break

                summary = self.scraper.parser.parse_catalog_page(
                    html,
                    page_url=catalog_url
                )
                page_urls = [url for url in summary.book_urls if url not in seen_urls]

                for url in page_urls:
                    seen_urls.add(url)

                page_stats = await self._process_book_urls(page_urls)
                self._merge_stats(stats, page_stats)

                if not summary.has_next or not summary.book_urls:
                    break
                page += 1

            stats["total_processed"] = (
                stats["new_books"] + stats["changed_books"] + stats["unchanged_books"]
            )

            logger.info("Change detection completed", extra=stats)
            return stats

        finally:
            await self.close()

    async def _process_book_urls(self, urls: List[str]) -> Dict[str, int]:
        """Process a batch of book URLs and aggregate stats."""
        if not urls:
            return self._empty_stats()

        tasks = [self._process_single_book(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        stats = self._empty_stats()

        for result in results:
            if isinstance(result, dict):
                self._merge_stats(stats, result)
            elif isinstance(result, Exception):
                logger.error(
                    "Unexpected error during change detection",
                    exc_info=True
                )
                stats["errors"] += 1

        return stats

    async def _process_single_book(self, url: str) -> Dict[str, int]:
        """Fetch, compare, and update a single book."""
        stats = self._empty_stats()

        if not self.scraper or not self.book_repo or not self.change_repo:
            stats["errors"] += 1
            return stats

        try:
            html = await self.scraper.client.fetch_html(url)
            book = self.scraper.parser.parse_book_page(html, url)
        except (HTTPClientError, ParsingError) as exc:
            logger.warning(
                "Failed to crawl book for change detection",
                extra={"url": url, "error": str(exc)}
            )
            if self.book_repo:
                await self.book_repo.record_failed_crawl(
                    url=url,
                    html=sanitize_html(html) if "html" in locals() else None,
                    error=str(exc),
                    stage="change_detection"
                )
            stats["errors"] += 1
            return stats
        except Exception as exc:
            logger.error(
                "Unexpected error during change detection crawl",
                extra={"url": url, "error": str(exc)},
                exc_info=True
            )
            if self.book_repo:
                await self.book_repo.record_failed_crawl(
                    url=url,
                    html=sanitize_html(html) if "html" in locals() else None,
                    error=str(exc),
                    stage="change_detection"
                )
            stats["errors"] += 1
            return stats

        existing_doc = await self.book_repo.collection.find_one(
            {"source_url": str(book.source_url)}
        )

        if not existing_doc:
            book_id = await self.book_repo.upsert_book(book)
            await self.detect_new_book(book, book_id)
            stats["new_books"] += 1
            return stats

        book_id = str(existing_doc.get("_id"))
        old_book = self.book_repo._document_to_book(existing_doc)

        if old_book.content_hash == book.content_hash:
            stats["unchanged_books"] += 1
            return stats

        changes = await self.compare_and_log_changes(old_book, book, book_id)

        if not changes:
            stats["unchanged_books"] += 1
            return stats

        stats["changed_books"] += 1
        for change in changes:
            change_type = change.get("type")
            if change_type == "price_change":
                stats["price_changes"] += 1
            elif change_type == "availability_change":
                stats["availability_changes"] += 1
            elif change_type == "description_change":
                stats["description_changes"] += 1
            elif change_type == "rating_change":
                stats["rating_changes"] += 1

        await self.book_repo.upsert_book(book)
        return stats

    async def compare_and_log_changes(
        self,
        old_book: Book,
        new_book: Book,
        book_id: str
    ) -> List[dict]:
        """
        Compare two book versions and log changes.

        Args:
            old_book: Previously stored book
            new_book: Newly crawled book
            book_id: Book ID

        Returns:
            List of change dictionaries
        """
        changes: List[dict] = []

        # Check price changes
        if old_book.price_incl_tax != new_book.price_incl_tax:
            price_delta = new_book.price_incl_tax - old_book.price_incl_tax
            pct_change = 0.0
            if old_book.price_incl_tax:
                pct_change = (price_delta / old_book.price_incl_tax) * 100
            changes.append({
                "type": "price_change",
                "field": "price_incl_tax",
                "old": old_book.price_incl_tax,
                "new": new_book.price_incl_tax,
                "percent_change": round(pct_change, 2)
            })
            await self.change_repo.log_change(
                book_id=book_id,
                book_name=new_book.name,
                change_type="price_change",
                field_name="price_incl_tax",
                old_value=str(old_book.price_incl_tax),
                new_value=str(new_book.price_incl_tax)
            )
            if pct_change <= -10:
                logger.warning(
                    "Significant price drop detected",
                    extra={
                        "book_id": book_id,
                        "book_name": new_book.name,
                        "old_price": old_book.price_incl_tax,
                        "new_price": new_book.price_incl_tax,
                        "percent_change": round(pct_change, 2)
                    }
                )

        if old_book.price_excl_tax != new_book.price_excl_tax:
            changes.append({
                "type": "price_change",
                "field": "price_excl_tax",
                "old": old_book.price_excl_tax,
                "new": new_book.price_excl_tax
            })
            await self.change_repo.log_change(
                book_id=book_id,
                book_name=new_book.name,
                change_type="price_change",
                field_name="price_excl_tax",
                old_value=str(old_book.price_excl_tax),
                new_value=str(new_book.price_excl_tax)
            )

        # Check availability changes
        if old_book.availability != new_book.availability:
            changes.append({
                "type": "availability_change",
                "field": "availability",
                "old": old_book.availability,
                "new": new_book.availability
            })
            await self.change_repo.log_change(
                book_id=book_id,
                book_name=new_book.name,
                change_type="availability_change",
                field_name="availability",
                old_value=old_book.availability,
                new_value=new_book.availability
            )
            logger.info(
                "Availability change detected",
                extra={
                    "book_id": book_id,
                    "book_name": new_book.name,
                    "old": old_book.availability,
                    "new": new_book.availability
                }
            )

        # Check description changes
        if (old_book.description or "") != (new_book.description or ""):
            changes.append({
                "type": "description_change",
                "field": "description",
                "old": old_book.description or "",
                "new": new_book.description or ""
            })
            await self.change_repo.log_change(
                book_id=book_id,
                book_name=new_book.name,
                change_type="description_change",
                field_name="description",
                old_value=old_book.description or "",
                new_value=new_book.description or ""
            )

        # Check rating changes
        old_rating = (
            old_book.rating.value if hasattr(old_book.rating, "value") else str(old_book.rating)
        )
        new_rating = (
            new_book.rating.value if hasattr(new_book.rating, "value") else str(new_book.rating)
        )
        if old_rating != new_rating:
            changes.append({
                "type": "rating_change",
                "field": "rating",
                "old": old_rating,
                "new": new_rating
            })
            await self.change_repo.log_change(
                book_id=book_id,
                book_name=new_book.name,
                change_type="rating_change",
                field_name="rating",
                old_value=old_rating,
                new_value=new_rating
            )

        return changes

    async def detect_new_book(self, book: Book, book_id: str) -> None:
        """
        Log a newly detected book.

        Args:
            book: New book
            book_id: Book ID
        """
        await self.change_repo.log_change(
            book_id=book_id,
            book_name=book.name,
            change_type="new_book",
            field_name=None,
            old_value=None,
            new_value=None
        )
        logger.info("Detected new book", extra={"book_name": book.name})

    @staticmethod
    def _empty_stats() -> Dict[str, int]:
        """Initialize a stats dictionary."""
        return {
            "new_books": 0,
            "changed_books": 0,
            "unchanged_books": 0,
            "price_changes": 0,
            "availability_changes": 0,
            "description_changes": 0,
            "rating_changes": 0,
            "errors": 0,
            "total_processed": 0,
        }

    @staticmethod
    def _merge_stats(base: Dict[str, int], delta: Dict[str, int]) -> None:
        """Merge two stats dictionaries in-place."""
        for key, value in delta.items():
            base[key] = base.get(key, 0) + value


async def main():
    """CLI entry point for manual change detection runs."""
    setup_logging()
    logger.info("Starting change detector CLI")
    detector = ChangeDetector()
    stats = await detector.detect_changes()
    logger.info("Change detector finished", extra=stats)


if __name__ == "__main__":
    asyncio.run(main())
