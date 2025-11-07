"""Database index creation utilities."""

from motor.motor_asyncio import AsyncIOMotorDatabase

from config.logging_config import get_logger

logger = get_logger(__name__)


async def create_indexes(db: AsyncIOMotorDatabase) -> None:
    """
    Create all required database indexes.

    Args:
        db: MongoDB database instance
    """
    try:
        # Books collection indexes
        books_collection = db.books

        # Unique index on source_url
        await books_collection.create_index(
            "source_url",
            unique=True,
            name="source_url_unique"
        )

        # Single field indexes
        await books_collection.create_index("category", name="category_idx")
        await books_collection.create_index("price_incl_tax", name="price_idx")
        await books_collection.create_index("rating", name="rating_idx")
        await books_collection.create_index("content_hash", name="content_hash_idx")
        await books_collection.create_index("crawl_timestamp", name="crawl_timestamp_idx")
        await books_collection.create_index("status", name="status_idx")

        # Compound indexes for common queries
        await books_collection.create_index(
            [("category", 1), ("price_incl_tax", 1)],
            name="category_price_idx"
        )
        await books_collection.create_index(
            [("rating", 1), ("num_reviews", -1)],
            name="rating_reviews_idx"
        )

        # Text index for search
        await books_collection.create_index(
            [("name", "text"), ("description", "text")],
            name="text_search_idx"
        )

        # Changes collection indexes
        changes_collection = db.changes
        await changes_collection.create_index("detected_at", name="detected_at_idx")
        await changes_collection.create_index("book_id", name="book_id_idx")
        await changes_collection.create_index("change_type", name="change_type_idx")
        await changes_collection.create_index(
            [("detected_at", -1), ("change_type", 1)],
            name="detected_at_change_type_idx"
        )

        # Crawler state collection indexes
        state_collection = db.crawler_state
        await state_collection.create_index("status", name="status_idx")

        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}", exc_info=True)
        raise

