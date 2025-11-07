"""Async HTTP client wrapper with retry logic and rate limiting."""

import asyncio
from typing import Optional

import httpx

from config.logging_config import get_logger
from config.settings import settings
from utils.exceptions import HTTPClientError
from utils.retry import retry_on_http_error

logger = get_logger(__name__)


class HTTPClient:
    """Async HTTP client with retry, rate limiting, and connection pooling."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
        max_concurrent: Optional[int] = None
    ):
        """
        Initialize HTTP client.

        Args:
            base_url: Base URL for requests
            timeout: Request timeout in seconds
            max_concurrent: Maximum concurrent requests
        """
        self.base_url = base_url or str(settings.crawler.base_url)
        self.timeout = timeout or settings.crawler.request_timeout
        self.max_concurrent = max_concurrent or settings.crawler.max_concurrent_requests
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def start(self) -> None:
        """Initialize HTTP client."""
        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100
        )
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            limits=limits,
            headers={
                "User-Agent": settings.crawler.user_agent
            },
            follow_redirects=True
        )
        logger.info(f"HTTP client initialized: {self.base_url}")

    async def close(self) -> None:
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            logger.debug("HTTP client closed")

    @retry_on_http_error()
    async def fetch(self, url: str, **kwargs) -> httpx.Response:
        """
        Fetch URL with retry logic and rate limiting.

        Args:
            url: URL to fetch
            **kwargs: Additional arguments for httpx request

        Returns:
            HTTP response

        Raises:
            HTTPClientError: If request fails after retries
        """
        if not self.client:
            await self.start()

        async with self.semaphore:
            try:
                logger.debug(f"Fetching URL: {url}")
                response = await self.client.get(url, **kwargs)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP error {e.response.status_code} for {url}",
                    extra={"url": url, "status_code": e.response.status_code}
                )
                raise HTTPClientError(f"HTTP {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error(f"Request error for {url}: {e}", exc_info=True)
                raise HTTPClientError(f"Request failed: {str(e)}")

    async def fetch_text(self, url: str, **kwargs) -> str:
        """
        Fetch URL and return text content.

        Args:
            url: URL to fetch
            **kwargs: Additional arguments for httpx request

        Returns:
            Response text content
        """
        response = await self.fetch(url, **kwargs)
        return response.text

    async def fetch_html(self, url: str, **kwargs) -> str:
        """
        Fetch URL and return HTML content (alias for fetch_text).

        Args:
            url: URL to fetch
            **kwargs: Additional arguments for httpx request

        Returns:
            Response HTML content
        """
        return await self.fetch_text(url, **kwargs)

