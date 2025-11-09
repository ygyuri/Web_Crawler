"""Unit tests for HTTP client wrapper."""

import asyncio

import httpx
import pytest

from crawler.client import HTTPClient
from utils.exceptions import HTTPClientError


@pytest.mark.asyncio
async def test_http_client_fetch_success(monkeypatch, respx_mock):
    monkeypatch.setattr(
        "config.settings.settings.crawler.user_agents",
        ["TestAgent/1.0", "TestAgent/2.0"]
    )

    respx_mock.get("https://example.com/test").respond(200, text="ok")

    async with HTTPClient(base_url="https://example.com", max_concurrent=2) as client:
        response = await client.fetch("/test")

    assert response.status_code == 200
    assert response.text == "ok"


@pytest.mark.asyncio
async def test_http_client_circuit_breaker(monkeypatch, respx_mock):
    monkeypatch.setattr("config.settings.settings.crawler.circuit_breaker_failure_threshold", 1)
    monkeypatch.setattr("config.settings.settings.crawler.circuit_breaker_reset_timeout", 1)
    monkeypatch.setattr("config.settings.settings.crawler.circuit_breaker_half_open_max_calls", 1)

    respx_mock.get("https://example.com/fail").mock(side_effect=httpx.ConnectError("boom", request=httpx.Request("GET", "https://example.com/fail")))

    async with HTTPClient(base_url="https://example.com") as client:
        with pytest.raises(HTTPClientError):
            await client.fetch("/fail")

        with pytest.raises(HTTPClientError) as exc:
            await client.fetch("/fail")

        assert "Circuit breaker open" in str(exc.value)



