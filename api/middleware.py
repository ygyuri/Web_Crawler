"""Rate limiting middleware."""

import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware per API key."""

    def __init__(self, app, requests_per_hour: int = None):
        """
        Initialize rate limiter.

        Args:
            app: FastAPI application
            requests_per_hour: Requests per hour limit
        """
        super().__init__(app)
        self.requests_per_hour = requests_per_hour or settings.api.rate_limit
        self.requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting.

        Args:
            request: HTTP request
            call_next: Next middleware handler

        Returns:
            HTTP response
        """
        # Get API key from header
        api_key = request.headers.get(settings.api.api_key_header)

        if api_key:
            # Check rate limit
            if not self._check_rate_limit(api_key):
                logger.warning(f"Rate limit exceeded for API key: {api_key[:8]}...")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                    headers={"Retry-After": "3600"}
                )

        response = await call_next(request)
        return response

    def _check_rate_limit(self, api_key: str) -> bool:
        """
        Check if API key is within rate limit.

        Args:
            api_key: API key

        Returns:
            True if within limit
        """
        now = time.time()
        hour_ago = now - 3600

        # Clean old requests
        self.requests[api_key] = [
            req_time for req_time in self.requests[api_key]
            if req_time > hour_ago
        ]

        # Check limit
        if len(self.requests[api_key]) >= self.requests_per_hour:
            return False

        # Add current request
        self.requests[api_key].append(now)
        return True

