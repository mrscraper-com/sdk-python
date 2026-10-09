"""Unit tests for fetch HTML and Google SERP request construction."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from mrscraper import APIError, MrScraper


@pytest.fixture
def recorded_client():
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"ok": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    yield client, requests


def request_json(request: httpx.Request) -> dict[str, Any]:
    return json.loads(request.content)


@pytest.mark.asyncio
async def test_fetch_content_supports_cli_controls(recorded_client):
    http_client, requests = recorded_client
    client = MrScraper("test-token", http_client=http_client)

    await client.fetch_content(
        "https://example.com/page",
        timeout=45,
        geo_code="ID",
        browser_rendering=True,
        super=True,
        wait_for_selector=".ready",
        home_page=True,
        screenshot=True,
        block_resources=True,
        max_retries=4,
        token_cap=100,
        use_proxy=False,
        proxy="user:pass@proxy.example:8000",
        proxy_country="SG",
        bypass_proxy=True,
        cookie_jar="domain=example.com&country=sg&max_used=10&max_age=50m",
        headers={"accept-language": "en-US"},
        stream=True,
        discard_token_secret="discard-secret",
    )

    request = requests[0]
    payload = request_json(request)
    assert request.method == "POST"
    assert request.url.path == "/"
    assert payload == {"url": "https://example.com/page", "maxRetries": 4, "tokenCap": 100}
    assert request.url.params["browserRendering"] == "true"
    assert request.url.params["super"] == "true"
    assert request.url.params["geoCode"] == "ID"
    assert request.url.params["waitForSelector"] == ".ready"
    assert request.url.params["warmStart"] == "true"
    assert "homePage" not in request.url.params
    assert request.url.params["screenshot"] == "true"
    assert request.url.params["blockResources"] == "true"
    assert request.url.params["useProxy"] == "false"
    assert request.url.params["proxy"] == "user:pass@proxy.example:8000"
    assert request.url.params["proxyCountry"] == "SG"
    assert request.url.params["bypassProxy"] == "true"
    assert request.url.params["cookieJar"].startswith("domain=example.com")
    assert json.loads(request.url.params["headers"]) == {"accept-language": "en-US"}
    assert request.url.params["stream"] == "true"
    assert request.url.params["token"] == "test-token"
    assert request.url.params["timeout"] == "45"
    assert request.headers["authorization"] == "Bearer test-token"
    assert request.headers["x-api-token"] == "test-token"
    assert request.headers["x-discard-token-secret"] == "discard-secret"
    assert not http_client.is_closed
    await http_client.aclose()


@pytest.mark.asyncio
async def test_fetch_content_screenshot_forces_browser_rendering(recorded_client):
    http_client, requests = recorded_client
    client = MrScraper("test-token", http_client=http_client)

    await client.fetch_content("https://example.com", screenshot=True, browser_rendering=False)
    await client.fetch_content("https://example.com")

    assert request_json(requests[0]) == {"url": "https://example.com", "maxRetries": 3}
    assert requests[0].url.params["screenshot"] == "true"
    assert requests[0].url.params["browserRendering"] == "true"
    assert "screenshot" not in request_json(requests[1])
    assert "screenshot" not in requests[1].url.params
    assert "browserRendering" not in requests[1].url.params
    assert "warmStart" not in requests[1].url.params
    await http_client.aclose()


@pytest.mark.asyncio
async def test_fetch_content_requests_html_markdown_and_screenshot_together(recorded_client):
    http_client, requests = recorded_client
    client = MrScraper("test-token", http_client=http_client)

    await client.fetch_content("https://example.com", html=True, markdown=True, screenshot=True)

    params = requests[0].url.params
    assert params["html"] == "true"
    assert params["markdown"] == "true"
    assert params["screenshot"] == "true"
    await http_client.aclose()


@pytest.mark.asyncio
async def test_fetch_content_super_query_parameter(recorded_client):
    http_client, requests = recorded_client
    client = MrScraper("test-token", http_client=http_client)

    await client.fetch_content("https://example.com", super=True)
    await client.fetch_content("https://example.com")

    assert "super" not in request_json(requests[0])
    assert requests[0].url.params["super"] == "true"
    assert "super" not in requests[1].url.params
    await http_client.aclose()


@pytest.mark.asyncio
async def test_fetch_content_error_does_not_expose_query_token():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"message": "invalid request"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = MrScraper("secret-token", http_client=http_client)
        with pytest.raises(APIError) as error:
            await client.fetch_content("https://example.com", screenshot=True)

    assert error.value.status_code == 422
    assert "secret-token" not in str(error.value)


@pytest.mark.asyncio
async def test_google_serp_uses_v2_and_normalizes_google_url(recorded_client):
    http_client, requests = recorded_client
    client = MrScraper("test-token", http_client=http_client)

    await client.google_serp(
        "https://www.google.com/search?q=running+shoes&gl=us&hl=en&start=20",
        raw=False,
        render_js=True,
    )

    request = requests[0]
    assert request.url.path == "/api/google/serp/v2/sync"
    assert request_json(request) == {
        "query": "running shoes",
        "region": "us",
        "language": "en",
        "page": 3,
        "format": "json",
        "renderJs": True,
    }
    await http_client.aclose()


@pytest.mark.asyncio
async def test_google_serp_keeps_raw_compatibility(recorded_client):
    http_client, requests = recorded_client
    client = MrScraper("test-token", http_client=http_client)

    await client.google_serp("iphone 17")

    assert request_json(requests[0]) == {
        "query": "iphone 17",
        "format": "html",
        "renderJs": False,
    }
    await http_client.aclose()
