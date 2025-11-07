"""MongoDB async connection management."""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)


class Database:
    """MongoDB database connection manager."""

    client: Optional[AsyncIOMotorClient] = None
    database: Optional[AsyncIOMotorDatabase] = None

    @classmethod
    async def connect(cls) -> None:
        """Establish MongoDB connection."""
        try:
            cls.client = AsyncIOMotorClient(
                settings.database.url,
                maxPoolSize=settings.database.max_pool_size,
                minPoolSize=settings.database.min_pool_size,
            )
            cls.database = cls.client[settings.database.db_name]
            # Test connection
            await cls.client.admin.command("ping")
            logger.info(
                f"Connected to MongoDB: {settings.database.db_name}",
                extra={"db_name": settings.database.db_name}
            )
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}", exc_info=True)
            raise

    @classmethod
    async def disconnect(cls) -> None:
        """Close MongoDB connection."""
        if cls.client:
            cls.client.close()
            logger.info("Disconnected from MongoDB")

    @classmethod
    async def health_check(cls) -> bool:
        """Check database health."""
        try:
            if cls.client is None:
                return False
            await cls.client.admin.command("ping")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        """Get database instance."""
        if cls.database is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return cls.database

