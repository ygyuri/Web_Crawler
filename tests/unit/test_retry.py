"""Unit tests for retry utilities."""

import asyncio
from typing import Callable

import httpx
import pytest

from utils.retry import retry_on_http_error


@pytest.mark.asyncio
async def test_retry_decorator_retries_on_http_error():
    attempts = 0

    @retry_on_http_error(max_attempts=3, backoff_multiplier=0.01)
    async def flaky_call() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise httpx.ConnectError("boom", request=httpx.Request("GET", "https://example.com"))
        return "ok"

    result = await flaky_call()
    assert result == "ok"
    assert attempts == 3


@pytest.mark.asyncio
async def test_retry_decorator_does_not_retry_non_http_error():
    @retry_on_http_error(max_attempts=2, backoff_multiplier=0.01)
    async def failing_call():
        raise ValueError("not http error")

    with pytest.raises(ValueError):
        await failing_call()



