"""Retry decorators using tenacity."""

from functools import wraps
from typing import Callable, TypeVar, Any

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryCallState
)
import httpx

from config.logging_config import get_logger
from config.settings import settings
from utils.exceptions import HTTPClientError

logger = get_logger(__name__)

T = TypeVar("T")


def retry_on_http_error(
    max_attempts: int = None,
    backoff_multiplier: float = None
) -> Callable:
    """
    Decorator for retrying HTTP requests on transient errors.

    Args:
        max_attempts: Maximum retry attempts (defaults to config)
        backoff_multiplier: Exponential backoff multiplier (defaults to config)

    Returns:
        Decorated function
    """
    max_attempts = max_attempts or settings.crawler.max_retries
    backoff_multiplier = backoff_multiplier or settings.crawler.retry_backoff

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(
                multiplier=backoff_multiplier,
                min=1,
                max=10
            ),
            retry=retry_if_exception_type((
                httpx.HTTPError,
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.NetworkError
            )),
            reraise=True,
            before_sleep=_log_retry_attempt
        )
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    f"Retrying {func.__name__} after error: {e}",
                    extra={"function": func.__name__}
                )
                raise

        return wrapper
    return decorator


def _log_retry_attempt(retry_state: RetryCallState) -> None:
    """Log retry attempt."""
    logger.warning(
        f"Retrying {retry_state.fn.__name__} "
        f"(attempt {retry_state.attempt_number}/{retry_state.outcome})"
    )

