"""API key authentication."""

from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)

api_key_header = APIKeyHeader(
    name=settings.api.api_key_header,
    auto_error=False
)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Verify API key from header.

    Args:
        api_key: API key from header

    Returns:
        API key if valid

    Raises:
        HTTPException: If API key is invalid
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key required"
        )

    valid_keys = settings.api.api_keys
    if not valid_keys:
        logger.warning("No API keys configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API authentication not configured"
        )

    if api_key not in valid_keys:
        logger.warning(f"Invalid API key attempted: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )

    return api_key

