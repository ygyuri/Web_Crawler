"""FastAPI dependencies for dependency injection."""

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


def get_book_repository(db: AsyncIOMotorDatabase = None) -> BookRepository:
    """
    Get book repository instance.

    Args:
        db: Database instance (optional, will be fetched if not provided)

    Returns:
        BookRepository instance
    """
    if db is None:
        db = Database.get_database()
    return BookRepository(db)


def get_change_repository(db: AsyncIOMotorDatabase = None) -> ChangeRepository:
    """
    Get change repository instance.

    Args:
        db: Database instance (optional, will be fetched if not provided)

    Returns:
        ChangeRepository instance
    """
    if db is None:
        db = Database.get_database()
    return ChangeRepository(db)

