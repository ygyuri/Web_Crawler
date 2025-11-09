"""CLI entry point for crawler."""

import argparse
import asyncio
import sys
from typing import Optional

from config.logging_config import setup_logging, get_logger
from crawler.scraper import BookScraper

logger = get_logger(__name__)


def _parse_bool(value: str) -> bool:
    """Parse boolean CLI flags that may be provided as --flag=false."""
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError(f"Invalid boolean value: {value}")


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Book crawler CLI")
    parser.add_argument(
        "--resume",
        type=_parse_bool,
        default=True,
        help="Resume from last saved state (default: true)",
        metavar="BOOL",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum number of catalog pages to crawl (default: unlimited)",
    )
    return parser.parse_args(argv)


async def main(argv: Optional[list[str]] = None):
    """Main entry point."""
    args = _parse_args(argv)

    setup_logging()
    logger.info("Starting book crawler")

    scraper = BookScraper()
    try:
        total_books = await scraper.crawl_all_books(
            resume=args.resume,
            max_pages=args.max_pages,
        )
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

