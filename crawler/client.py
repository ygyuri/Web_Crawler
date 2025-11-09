"""Async HTTP client wrapper with retry logic, rate limiting, User-Agent rotation, and circuit breaker."""

import asyncio
import random
import time
from typing import Dict, Optional

import httpx

from config.logging_config import get_logger
from config.settings import settings
from utils.exceptions import HTTPClientError
from utils.retry import retry_on_http_error

logger = get_logger(__name__)


class HTTPClient:
    """Async HTTP client with retry, rate limiting, connection pooling, and resiliency primitives."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
        max_concurrent: Optional[int] = None
    ):
        """
        Initialize HTTP client.

        Args:
            base_url: Base URL for requests.
            timeout: Request timeout in seconds.
            max_concurrent: Maximum concurrent requests.
        """
        self.base_url = base_url or str(settings.crawler.base_url)
        self.timeout = timeout or settings.crawler.request_timeout
        self.max_concurrent = max_concurrent or settings.crawler.max_concurrent_requests
        self.semaphore = asyncio.Semaphore(self.max_concurrent)

        self.user_agents = settings.crawler.user_agents or [settings.crawler.user_agent]
        if settings.crawler.user_agent and settings.crawler.user_agent not in self.user_agents:
            self.user_agents.append(settings.crawler.user_agent)

        self.circuit_failure_threshold = settings.crawler.circuit_breaker_failure_threshold
        self.circuit_reset_timeout = settings.crawler.circuit_breaker_reset_timeout
        self.circuit_half_open_max_calls = settings.crawler.circuit_breaker_half_open_max_calls

        self._client: Optional[httpx.AsyncClient] = None
        self._circuit_lock = asyncio.Lock()
        self._circuit_state = "closed"
        self._failure_count = 0
        self._circuit_open_until: Optional[float] = None
        self._half_open_attempts = 0

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def start(self) -> None:
        """Initialize HTTP client."""
        if self._client is not None:
            return

        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100
        )
        default_headers = {
            "User-Agent": self.user_agents[0]
        }
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            limits=limits,
            headers=default_headers,
            follow_redirects=True
        )
        logger.info("HTTP client initialized", extra={"base_url": self.base_url})

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.debug("HTTP client closed")

    @retry_on_http_error()
    async def fetch(self, url: str, **kwargs) -> httpx.Response:
        """
        Fetch URL with retry logic, circuit breaker, and rate limiting.

        Args:
            url: URL to fetch.
            **kwargs: Additional arguments for httpx request.

        Returns:
            HTTP response.

        Raises:
            HTTPClientError: If request fails, circuit is open, or retries exhausted.
        """
        if not self._client:
            await self.start()

        await self._check_circuit_ready()

        headers = self._build_headers(kwargs.pop("headers", None))

        async with self.semaphore:
            try:
                logger.debug("Fetching URL", extra={"url": url})
                response = await self._client.get(url, headers=headers, **kwargs)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                await self._record_failure(exc)
                logger.error(
                    "HTTP status error",
                    extra={"url": url, "status_code": exc.response.status_code}
                )
                raise HTTPClientError(f"HTTP {exc.response.status_code}: {exc.response.text}") from exc
            except httpx.RequestError as exc:
                await self._record_failure(exc)
                logger.error("Request error", extra={"url": url, "error": str(exc)}, exc_info=True)
                raise HTTPClientError(f"Request failed: {exc}") from exc
            else:
                await self._record_success()
                return response

    async def fetch_text(self, url: str, **kwargs) -> str:
        """
        Fetch URL and return text content.

        Args:
            url: URL to fetch.
            **kwargs: Additional arguments for httpx request.

        Returns:
            Response text content.
        """
        response = await self.fetch(url, **kwargs)
        return response.text

    async def fetch_html(self, url: str, **kwargs) -> str:
        """
        Fetch URL and return HTML content (alias for fetch_text).

        Args:
            url: URL to fetch.
            **kwargs: Additional arguments for httpx request.

        Returns:
            Response HTML content.
        """
        return await self.fetch_text(url, **kwargs)

    def _build_headers(self, custom_headers: Optional[Dict[str, str]]) -> Dict[str, str]:
        """Merge custom headers with a rotated User-Agent."""
        headers = dict(custom_headers or {})
        headers.setdefault("User-Agent", random.choice(self.user_agents))
        return headers

    async def _check_circuit_ready(self) -> None:
        """Ensure circuit breaker permits executing the request."""
        async with self._circuit_lock:
            now = time.monotonic()
            if self._circuit_state == "open":
                if self._circuit_open_until and now >= self._circuit_open_until:
                    self._circuit_state = "half-open"
                    self._half_open_attempts = 0
                    logger.warning("Circuit breaker transitioning to half-open state")
                else:
                    raise HTTPClientError("Circuit breaker open: throttling outbound requests")

            if self._circuit_state == "half-open":
                if self._half_open_attempts >= self.circuit_half_open_max_calls:
                    raise HTTPClientError("Circuit breaker half-open limit reached")
                self._half_open_attempts += 1

    async def _record_success(self) -> None:
        """Reset circuit breaker on successful request."""
        async with self._circuit_lock:
            self._failure_count = 0
            if self._circuit_state != "closed":
                logger.info("Circuit breaker closed after successful probe")
            self._circuit_state = "closed"
            self._circuit_open_until = None
            self._half_open_attempts = 0

    async def _record_failure(self, exc: Exception) -> None:
        """Track failures and trip the circuit breaker when thresholds are exceeded."""
        async with self._circuit_lock:
            self._failure_count += 1
            if self._circuit_state == "half-open":
                self._trip_circuit(reason="Half-open probe failed", exc=exc)
            elif self._failure_count >= self.circuit_failure_threshold:
                self._trip_circuit(reason="Failure threshold reached", exc=exc)

    def _trip_circuit(self, reason: str, exc: Exception) -> None:
        """Trip the circuit breaker to open state."""
        self._circuit_state = "open"
        self._circuit_open_until = time.monotonic() + self.circuit_reset_timeout
        self._half_open_attempts = 0
        logger.error(
            "Circuit breaker opened",
            extra={
                "reason": reason,
                "cooldown_seconds": self.circuit_reset_timeout,
                "failure_count": self._failure_count,
                "exception": str(exc)
            }
        )

