"""Core async scraping logic."""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Tuple

from config.logging_config import get_logger
from config.settings import settings
from crawler.client import HTTPClient
from crawler.models import Book
from crawler.parser import BookParser, CatalogPageSummary
from crawler.state import StateManager
from database.connection import Database
from database.repositories.book_repository import BookRepository
from utils.exceptions import ParsingError, HTTPClientError
from utils.validators import sanitize_html

logger = get_logger(__name__)


class BookScraper:
    """Main scraper for crawling books from books.toscrape.com."""

    def __init__(self):
        """Initialize scraper."""
        self.client: Optional[HTTPClient] = None
        self.parser = BookParser()
        self.book_repo: Optional[BookRepository] = None
        self.state_manager = StateManager()
        self.base_url = str(settings.crawler.base_url)
        self._seen_urls: Set[str] = set()
        self._run_start: Optional[datetime] = None
        self._total_pages: Optional[int] = None

    async def initialize(self) -> None:
        """Initialize scraper components."""
        # Initialize database connection
        await Database.connect()
        db = Database.get_database()

        # Initialize repositories
        self.book_repo = BookRepository(db)

        # Initialize HTTP client
        self.client = HTTPClient()
        await self.client.start()

        # Initialize state manager
        await self.state_manager.initialize()

        # Reset run metadata
        self._seen_urls.clear()
        self._run_start = datetime.now(timezone.utc)
        self._total_pages = None

        logger.info("Scraper initialized")

    async def close(self) -> None:
        """Close scraper resources."""
        if self.client:
            await self.client.close()
        await Database.disconnect()
        logger.info("Scraper closed")

    async def crawl_all_books(
        self,
        resume: bool = True,
        max_pages: Optional[int] = None
    ) -> int:
        """
        Crawl all books from the website.

        Args:
            resume: Whether to resume from last page
            max_pages: Optional limit on number of catalog pages to crawl

        Returns:
            Total number of books crawled
        """
        failed_catalog_pages: List[int] = []
        try:
            await self.initialize()

            # Get starting page
            start_page = 1
            last_state = None

            if max_pages is not None and max_pages <= 0:
                raise ValueError("max_pages must be a positive integer")

            if resume:
                last_state = await self.state_manager.get_last_state()
                if last_state and last_state.last_page:
                    start_page = max(1, last_state.last_page)
                    logger.info(
                        "Resuming crawl",
                        extra={
                            "start_page": start_page,
                            "previous_status": last_state.status
                        }
                    )
            else:
                await self.state_manager.reset()

            # Update state to running
            await self.state_manager.save_state(
                last_page=start_page,
                total_books=0,
                status="running"
            )

            total_books = 0
            page = start_page
            pages_processed = 0
            last_processed_page = start_page - 1
            hit_max_page_limit = False

            while True:
                if max_pages is not None and pages_processed >= max_pages:
                    hit_max_page_limit = True
                    logger.info(
                        "Reached max pages limit; stopping crawl",
                        extra={
                            "max_pages": max_pages,
                            "pages_processed": pages_processed,
                            "current_page": page
                        }
                    )
                    break

                current_page = page
                try:
                    # Fetch catalog page
                    catalog_url = f"{self.base_url}/catalogue/page-{current_page}.html"
                    logger.info(f"Crawling page {current_page}: {catalog_url}")

                    html = await self.client.fetch_html(catalog_url)

                    # Extract catalog metadata
                    catalog_summary = self.parser.parse_catalog_page(
                        html,
                        page_url=catalog_url
                    )
                    if catalog_summary.total_pages:
                        self._total_pages = catalog_summary.total_pages
                    book_urls = catalog_summary.book_urls
                    if not book_urls:
                        logger.warning(f"No books found on page {current_page}")
                        break

                    # Crawl books concurrently
                    books_crawled = await self._crawl_books_batch(book_urls)
                    total_books += books_crawled

                    # Update state
                    await self.state_manager.save_state(
                        last_page=current_page,
                        total_books=total_books,
                        status="running"
                    )

                    # Emit progress metrics
                    self._log_progress(current_page, total_books)

                    # Check for next page
                    if not catalog_summary.has_next:
                        logger.info("Reached last page")
                        break

                    page = current_page + 1

                except HTTPClientError as e:
                    logger.error(
                        "HTTP error while crawling catalog page",
                        extra={
                            "page": current_page,
                            "url": catalog_url,
                            "error": str(e)
                        }
                    )
                    failed_catalog_pages.append(current_page)
                    # Continue to next page
                    page = current_page + 1
                    continue
                except Exception as e:
                    logger.error(
                        f"Error crawling page {current_page}: {e}",
                        exc_info=True
                    )
                    # Save error state
                    await self.state_manager.save_state(
                        last_page=current_page,
                        total_books=total_books,
                        status="error"
                    )
                    raise
                finally:
                    pages_processed += 1
                    last_processed_page = current_page

            # Mark as completed
            await self.state_manager.save_state(
                last_page=max(last_processed_page, start_page),
                total_books=total_books,
                status="idle"
            )

            if hit_max_page_limit:
                logger.info(
                    "Crawl stopped after reaching configured max pages",
                    extra={
                        "max_pages": max_pages,
                        "pages_processed": pages_processed,
                        "last_page": last_processed_page
                    }
                )

            logger.info(f"Crawl completed: {total_books} books crawled")

            if failed_catalog_pages and not hit_max_page_limit:
                await self._retry_catalog_pages(failed_catalog_pages, total_books)
            return total_books

        finally:
            await self.close()

    async def _crawl_books_batch(self, book_urls: List[str]) -> int:
        """
        Crawl a batch of books concurrently.

        Args:
            book_urls: List of book URLs

        Returns:
            Number of successfully crawled books
        """
        urls_to_crawl = await self._filter_urls_for_crawl(book_urls)
        if not urls_to_crawl:
            logger.debug("All books on page already fresh; skipping fetch")
            return 0

        max_attempts = 2
        attempt = 1
        remaining = urls_to_crawl
        success_count = 0

        while remaining and attempt <= max_attempts:
            logger.debug(
                "Crawling book batch",
                extra={"attempt": attempt, "batch_size": len(remaining)}
            )
            tasks = [self._crawl_single_book(url) for url in remaining]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            next_remaining: List[str] = []
            for url, result in zip(remaining, results):
                if isinstance(result, Book):
                    success_count += 1
                elif isinstance(result, Exception):
                    logger.warning(
                        "Book crawl failed",
                        extra={"url": url, "attempt": attempt, "error": str(result)}
                    )
                    if attempt < max_attempts:
                        next_remaining.append(url)
                else:
                    logger.debug(
                        "Book crawl skipped",
                        extra={"url": url}
                    )

            if next_remaining:
                backoff_seconds = 2 ** attempt
                logger.info(
                    "Retrying failed book crawls after backoff",
                    extra={
                        "remaining": len(next_remaining),
                        "wait_seconds": backoff_seconds
                    }
                )
                await asyncio.sleep(backoff_seconds)

            remaining = next_remaining
            attempt += 1

        # Record any remaining failures after final attempt
        if remaining and self.book_repo:
            for url in remaining:
                await self.book_repo.record_failed_crawl(
                    url=url,
                    html=None,
                    error="Max crawl attempts exceeded",
                    stage="fetch"
                )

        return success_count

    async def _crawl_single_book(self, url: str) -> Optional[Book]:
        """
        Crawl a single book page.

        Args:
            url: Book page URL

        Returns:
            Book model or None if failed
        """
        try:
            # Fetch HTML
            html = await self.client.fetch_html(url)

            # Parse book data
            book = self.parser.parse_book_page(html, url)

            # Save to database
            if self.book_repo:
                await self.book_repo.upsert_book(book)
                logger.debug(f"Crawled book: {book.name}")

            return book

        except ParsingError as e:
            logger.warning(f"Parsing error for {url}: {e}")
            if self.book_repo:
                await self.book_repo.record_failed_crawl(
                    url=url,
                    html=sanitize_html(html),
                    error=str(e),
                    stage="parse"
                )
            return None
        except HTTPClientError as e:
            logger.warning(f"HTTP error for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error crawling {url}: {e}", exc_info=True)
            if self.book_repo:
                await self.book_repo.record_failed_crawl(
                    url=url,
                    html=sanitize_html(html) if "html" in locals() else None,
                    error=str(e),
                    stage="unknown"
                )
            return None

    async def _filter_urls_for_crawl(self, urls: List[str]) -> List[str]:
        """Filter URLs to avoid re-crawling fresh or duplicate entries."""
        filtered: List[str] = []
        if not urls:
            return filtered

        metadata: Dict[str, Dict] = {}
        if self.book_repo:
            metadata = await self.book_repo.get_existing_metadata_map(urls)

        recrawl_cutoff = None
        if settings.crawler.recrawl_interval_hours > 0:
            recrawl_cutoff = datetime.now(timezone.utc) - timedelta(
                hours=settings.crawler.recrawl_interval_hours
            )

        for url in urls:
            if url in self._seen_urls:
                logger.debug("Skipping duplicate URL in current run", extra={"url": url})
                continue

            self._seen_urls.add(url)
            existing = metadata.get(url)
            if not existing:
                filtered.append(url)
                continue

            last_crawled = existing.get("crawl_timestamp")
            if recrawl_cutoff and isinstance(last_crawled, datetime):
                if last_crawled < recrawl_cutoff:
                    filtered.append(url)
                    continue
                logger.debug(
                    "Skipping recently crawled book",
                    extra={"url": url, "last_crawled": last_crawled.isoformat()}
                )
            else:
                # No timestamp available, safest to crawl
                filtered.append(url)

        return filtered

    async def _retry_catalog_pages(self, pages: List[int], total_books: int) -> None:
        """Retry catalog pages that previously failed."""
        unique_pages = sorted(set(pages))
        logger.info(
            "Retrying failed catalog pages",
            extra={"pages": unique_pages}
        )
        for page in unique_pages:
            catalog_url = f"{self.base_url}/catalogue/page-{page}.html"
            try:
                html = await self.client.fetch_html(catalog_url)
                catalog_summary = self.parser.parse_catalog_page(
                    html,
                    page_url=catalog_url
                )
                if catalog_summary.total_pages:
                    self._total_pages = catalog_summary.total_pages
                books_crawled = await self._crawl_books_batch(catalog_summary.book_urls)
                total_books += books_crawled
                await self.state_manager.save_state(
                    last_page=page,
                    total_books=total_books,
                    status="running"
                )
                self._log_progress(page, total_books)
            except Exception as exc:
                logger.error(
                    "Retry of catalog page failed",
                    extra={"page": page, "url": catalog_url, "error": str(exc)},
                    exc_info=True
                )

    def _log_progress(self, current_page: int, total_books: int) -> None:
        """Log crawl progress metrics."""
        if not self._run_start:
            return

        elapsed_seconds = (datetime.now(timezone.utc) - self._run_start).total_seconds()
        if elapsed_seconds <= 0:
            return

        books_per_minute = total_books / (elapsed_seconds / 60)
        progress_pct = None
        if self._total_pages:
            progress_pct = round((current_page / self._total_pages) * 100, 2)

        logger.info(
            "Crawl progress",
            extra={
                "current_page": current_page,
                "total_pages": self._total_pages,
                "total_books": total_books,
                "books_per_minute": round(books_per_minute, 2),
                "progress_pct": progress_pct
            }
        )

