"""Core async scraping logic."""

import asyncio
from typing import List, Optional

from config.logging_config import get_logger
from config.settings import settings
from crawler.client import HTTPClient
from crawler.models import Book
from crawler.parser import BookParser
from crawler.state import StateManager
from database.connection import Database
from database.repositories.book_repository import BookRepository
from utils.exceptions import ParsingError, HTTPClientError

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

        logger.info("Scraper initialized")

    async def close(self) -> None:
        """Close scraper resources."""
        if self.client:
            await self.client.close()
        await Database.disconnect()
        logger.info("Scraper closed")

    async def crawl_all_books(self, resume: bool = True) -> int:
        """
        Crawl all books from the website.

        Args:
            resume: Whether to resume from last page

        Returns:
            Total number of books crawled
        """
        try:
            await self.initialize()

            # Get starting page
            start_page = 1
            if resume:
                state = await self.state_manager.get_last_state()
                if state.status == "running":
                    start_page = state.last_page
                    logger.info(f"Resuming crawl from page {start_page}")

            # Update state to running
            await self.state_manager.save_state(
                last_page=start_page,
                total_books=0,
                status="running"
            )

            total_books = 0
            page = start_page

            while True:
                try:
                    # Fetch catalog page
                    catalog_url = f"{self.base_url}/catalogue/page-{page}.html"
                    logger.info(f"Crawling page {page}: {catalog_url}")

                    html = await self.client.fetch_html(catalog_url)

                    # Extract book URLs
                    book_urls = self.parser.parse_book_urls(html)
                    if not book_urls:
                        logger.warning(f"No books found on page {page}")
                        break

                    # Crawl books concurrently
                    books_crawled = await self._crawl_books_batch(book_urls)
                    total_books += books_crawled

                    # Update state
                    await self.state_manager.save_state(
                        last_page=page,
                        total_books=total_books,
                        status="running"
                    )

                    # Check for next page
                    if not self.parser.has_next_page(html):
                        logger.info("Reached last page")
                        break

                    page += 1

                except HTTPClientError as e:
                    logger.error(f"HTTP error on page {page}: {e}")
                    # Continue to next page
                    page += 1
                    continue
                except Exception as e:
                    logger.error(f"Error crawling page {page}: {e}", exc_info=True)
                    # Save error state
                    await self.state_manager.save_state(
                        last_page=page,
                        total_books=total_books,
                        status="error"
                    )
                    raise

            # Mark as completed
            await self.state_manager.save_state(
                last_page=page,
                total_books=total_books,
                status="idle"
            )

            logger.info(f"Crawl completed: {total_books} books crawled")
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
        tasks = [self._crawl_single_book(url) for url in book_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"Failed to crawl book {book_urls[i]}: {result}",
                    exc_info=isinstance(result, Exception)
                )
            else:
                success_count += 1

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
            return None
        except HTTPClientError as e:
            logger.warning(f"HTTP error for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error crawling {url}: {e}", exc_info=True)
            return None

