"""MongoDB async connection management."""

import time
from typing import Dict, Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

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
        if cls.client is not None:
            return

        client_kwargs: Dict[str, object] = {
            "maxPoolSize": settings.database.max_pool_size,
            "minPoolSize": settings.database.min_pool_size,
            "serverSelectionTimeoutMS": settings.database.server_selection_timeout_ms,
            "connectTimeoutMS": settings.database.connect_timeout_ms,
            "socketTimeoutMS": settings.database.socket_timeout_ms,
            "retryWrites": True,
        }

        if settings.database.max_idle_time_ms:
            client_kwargs["maxIdleTimeMS"] = settings.database.max_idle_time_ms
        if settings.database.tls:
            client_kwargs["tls"] = True
            client_kwargs["tlsAllowInvalidCertificates"] = (
                settings.database.tls_allow_invalid_certificates
            )

        try:
            cls.client = AsyncIOMotorClient(
                settings.database.url,
                **client_kwargs,
            )
            cls.database = cls.client[settings.database.db_name]
            # Test connection
            await cls.client.admin.command("ping")
            logger.info(
                "Connected to MongoDB",
                extra={
                    "db_name": settings.database.db_name,
                    "max_pool_size": settings.database.max_pool_size,
                    "min_pool_size": settings.database.min_pool_size,
                }
            )
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}", exc_info=True)
            cls.client = None
            cls.database = None
            raise

    @classmethod
    async def disconnect(cls) -> None:
        """Close MongoDB connection."""
        if cls.client:
            cls.client.close()
            logger.info("Disconnected from MongoDB")
        cls.client = None
        cls.database = None

    @classmethod
    async def health_check(cls) -> Dict[str, object]:
        """Check database health."""
        if cls.client is None:
            return {
                "healthy": False,
                "error": "not_connected",
            }

        start = time.perf_counter()
        try:
            await cls.client.admin.command("ping")
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            return {
                "healthy": True,
                "latency_ms": latency_ms,
                "db_name": settings.database.db_name,
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
            }

    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        """Get database instance."""
        if cls.database is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return cls.database

