"""FastAPI dependencies for dependency injection."""

from typing import Tuple

from fastapi import Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from database.connection import Database
from database.repositories.book_repository import BookRepository
from database.repositories.change_repository import ChangeRepository


async def get_db() -> AsyncIOMotorDatabase:
    """
    Get MongoDB database instance.

    Returns:
        Database instance
    """
    return Database.get_database()


async def get_book_repository() -> BookRepository:
    """
    Get book repository instance.

    Returns:
        BookRepository instance
    """
    db = Database.get_database()
    return BookRepository(db)


async def get_change_repository() -> ChangeRepository:
    """
    Get change repository instance.

    Returns:
        ChangeRepository instance
    """
    db = Database.get_database()
    return ChangeRepository(db)


def get_pagination(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page")
) -> Tuple[int, int]:
    """
    Extract pagination parameters.

    Args:
        page: Requested page number.
        limit: Items per page.

    Returns:
        Tuple of (page, limit).
    """
    return page, limit

