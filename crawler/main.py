"""CLI entry point for crawler."""

import asyncio
import sys

from config.logging_config import setup_logging, get_logger
from crawler.scraper import BookScraper

logger = get_logger(__name__)


async def main():
    """Main entry point."""
    setup_logging()
    logger.info("Starting book crawler")

    scraper = BookScraper()
    try:
        total_books = await scraper.crawl_all_books(resume=True)
        logger.info(f"Crawl completed successfully: {total_books} books")
        return 0
    except Exception as e:
        logger.error(f"Crawl failed: {e}", exc_info=True)
        return 1
    finally:
        await scraper.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

