"""Book repository for database operations."""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from config.logging_config import get_logger
from crawler.models import Book

logger = get_logger(__name__)


class BookRepository:
    """Repository for book database operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize book repository.

        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.collection = db.books
        self.failed_collection = db.failed_crawls

    async def upsert_book(self, book: Book) -> str:
        """
        Insert or update a book by source_url.

        Args:
            book: Book model instance.

        Returns:
            The MongoDB document ID as a string.
        """
        try:
            book_dict = book.model_dump(exclude={"raw_html"})
            # Convert HttpUrl to string
            book_dict["source_url"] = str(book_dict["source_url"])
            book_dict["image_url"] = str(book_dict["image_url"])

            # Include raw_html if present
            if book.raw_html:
                book_dict["raw_html"] = book.raw_html

            # Check if book exists
            existing_doc = await self.collection.find_one(
                {"source_url": book_dict["source_url"]}
            )
            is_new = existing_doc is None

            result = await self.collection.update_one(
                {"source_url": book_dict["source_url"]},
                {"$set": book_dict},
                upsert=True
            )

            # Get the document ID
            if result.upserted_id:
                book_id = str(result.upserted_id)
            else:
                doc = await self.collection.find_one(
                    {"source_url": book_dict["source_url"]}
                )
                book_id = str(doc["_id"])

            logger.debug(
                "Upserted book",
                extra={
                    "book_id": book_id,
                    "source_url": str(book.source_url),
                    "is_new": is_new
                }
            )
            return book_id
        except Exception as e:
            logger.error(
                f"Failed to upsert book: {e}",
                extra={"source_url": str(book.source_url)},
                exc_info=True
            )
            raise

    async def get_existing_metadata_map(self, urls: List[str]) -> Dict[str, Dict]:
        """
        Fetch existing book metadata for a set of URLs.

        Args:
            urls: List of book source URLs.

        Returns:
            Mapping of URL to metadata (content_hash, crawl_timestamp).
        """
        if not urls:
            return {}

        cursor = self.collection.find(
            {"source_url": {"$in": urls}},
            {"source_url": 1, "content_hash": 1, "crawl_timestamp": 1}
        )

        metadata: Dict[str, Dict] = {}
        async for doc in cursor:
            metadata[doc["source_url"]] = {
                "content_hash": doc.get("content_hash"),
                "crawl_timestamp": doc.get("crawl_timestamp")
            }
        return metadata

    async def record_failed_crawl(
        self,
        url: str,
        html: Optional[str],
        error: str,
        stage: str
    ) -> None:
        """
        Persist failed crawl information for later inspection.

        Args:
            url: Source URL that failed.
            html: Raw HTML captured (if any).
            error: Error message.
            stage: Stage where failure occurred (e.g., "fetch", "parse").
        """
        try:
            doc = {
                "source_url": url,
                "raw_html": html,
                "error": error,
                "stage": stage,
                "last_attempt": datetime.now(timezone.utc)
            }
            await self.failed_collection.update_one(
                {"source_url": url},
                {"$set": doc},
                upsert=True
            )
            logger.debug(
                "Recorded failed crawl",
                extra={"source_url": url, "stage": stage}
            )
        except Exception as exc:
            logger.error(
                "Failed to record crawl failure",
                extra={"source_url": url, "stage": stage, "error": str(exc)},
                exc_info=True
            )

    async def get_book_by_url(self, url: str) -> Optional[Book]:
        """
        Get book by source URL.

        Args:
            url: Source URL

        Returns:
            Book model or None if not found
        """
        try:
            doc = await self.collection.find_one({"source_url": url})
            if doc:
                return self._document_to_book(doc)
            return None
        except Exception as e:
            logger.error(f"Failed to get book by URL: {e}", exc_info=True)
            raise

    async def get_book_by_id(self, book_id: str) -> Optional[Book]:
        """
        Get book by ID.

        Args:
            book_id: Book ID

        Returns:
            Book model or None if not found
        """
        try:
            doc = await self.collection.find_one({"_id": ObjectId(book_id)})
            if doc:
                return self._document_to_book(doc)
            return None
        except Exception as e:
            logger.error(f"Failed to get book by ID: {e}", exc_info=True)
            raise

    async def update_book(self, url: str, updates: Dict) -> bool:
        """
        Update book fields.

        Args:
            url: Source URL
            updates: Dictionary of fields to update

        Returns:
            True if updated, False if not found
        """
        try:
            result = await self.collection.update_one(
                {"source_url": url},
                {"$set": updates}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to update book: {e}", exc_info=True)
            raise

    async def find_books(
        self,
        filters: Dict,
        skip: int = 0,
        limit: int = 20,
        sort: Optional[List[tuple]] = None
    ) -> List[Book]:
        """
        Find books with filters, pagination, and sorting.

        Args:
            filters: MongoDB query filters
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            sort: List of (field, direction) tuples for sorting

        Returns:
            List of Book models
        """
        results = await self.find_books_with_ids(
            filters=filters,
            skip=skip,
            limit=limit,
            sort=sort
        )
        return [book for _, book in results]

    async def find_books_with_ids(
        self,
        filters: Dict,
        skip: int = 0,
        limit: int = 20,
        sort: Optional[List[tuple]] = None
    ) -> List[Tuple[str, Book]]:
        """
        Find books and return tuples of (book_id, Book).

        Args:
            filters: MongoDB query filters
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            sort: List of (field, direction) tuples for sorting

        Returns:
            List of tuples containing the document ID and Book model.
        """
        try:
            cursor = self.collection.find(filters)
            if sort:
                cursor = cursor.sort(sort)
            cursor = cursor.skip(skip).limit(limit)

            books: List[Tuple[str, Book]] = []
            async for doc in cursor:
                book_id = str(doc["_id"])
                book = self._document_to_book(doc)
                books.append((book_id, book))
            return books
        except Exception as exc:
            logger.error(
                "Failed to find books with ids",
                extra={"error": str(exc), "filters": filters},
                exc_info=True
            )
            raise

    async def count_books(self, filters: Dict) -> int:
        """
        Count books matching filters.

        Args:
            filters: MongoDB query filters

        Returns:
            Count of matching documents
        """
        try:
            return await self.collection.count_documents(filters)
        except Exception as e:
            logger.error(f"Failed to count books: {e}", exc_info=True)
            raise

    def _document_to_book(self, doc: Dict) -> Book:
        """
        Convert MongoDB document to Book model.

        Args:
            doc: MongoDB document

        Returns:
            Book model instance
        """
        # Convert ObjectId to string for source_url lookup
        doc_dict = dict(doc)
        # Remove _id from dict as it's not part of Book model
        doc_dict.pop("_id", None)
        doc_dict["source_url"] = doc_dict.get("source_url", "")
        doc_dict["image_url"] = doc_dict.get("image_url", "")
        return Book(**doc_dict)

