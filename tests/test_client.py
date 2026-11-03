"""Unit tests for scraper_api and web_search request construction."""

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
async def test_scraper_api_supports_cli_controls(recorded_client):
    http_client, requests = recorded_client
    client = MrScraper("test-token", http_client=http_client)

    await client._scrape(
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
async def test_scraper_api_screenshot_forces_browser_rendering(recorded_client):
    http_client, requests = recorded_client
    client = MrScraper("test-token", http_client=http_client)

    await client._scrape("https://example.com", screenshot=True, browser_rendering=False)
    await client._scrape("https://example.com")

    assert request_json(requests[0]) == {"url": "https://example.com", "maxRetries": 3}
    assert requests[0].url.params["screenshot"] == "true"
    assert requests[0].url.params["browserRendering"] == "true"
    assert "screenshot" not in request_json(requests[1])
    assert "screenshot" not in requests[1].url.params
    assert "browserRendering" not in requests[1].url.params
    assert "warmStart" not in requests[1].url.params
    await http_client.aclose()


@pytest.mark.asyncio
async def test_scraper_api_requests_html_markdown_and_screenshot_together(recorded_client):
    http_client, requests = recorded_client
    client = MrScraper("test-token", http_client=http_client)

    await client._scrape("https://example.com", html=True, markdown=True, screenshot=True)

    params = requests[0].url.params
    assert params["html"] == "true"
    assert params["markdown"] == "true"
    assert params["screenshot"] == "true"
    await http_client.aclose()


@pytest.mark.asyncio
async def test_scraper_api_super_query_parameter(recorded_client):
    http_client, requests = recorded_client
    client = MrScraper("test-token", http_client=http_client)

    await client._scrape("https://example.com", super=True)
    await client._scrape("https://example.com")

    assert "super" not in request_json(requests[0])
    assert requests[0].url.params["super"] == "true"
    assert "super" not in requests[1].url.params
    await http_client.aclose()


@pytest.mark.asyncio
async def test_scraper_api_error_does_not_expose_query_token():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"message": "invalid request"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = MrScraper("secret-token", http_client=http_client)
        with pytest.raises(APIError) as error:
            await client._scrape("https://example.com", screenshot=True)

    assert error.value.status_code == 422
    assert "secret-token" not in str(error.value)


@pytest.mark.asyncio
async def test_public_scraper_api_uses_get_with_url_and_retries_in_query(recorded_client):
    http_client, requests = recorded_client
    client = MrScraper("test-token", http_client=http_client)

    await client.scraper_api(
        "https://example.com/page?a=1&b=2",
        markdown=True,
        screenshot=True,
        wait_until="networkidle",
        token_cap=30,
    )

    request = requests[0]
    params = request.url.params
    assert request.method == "GET"
    assert request.content == b""
    assert params["url"] == "https://example.com/page?a=1&b=2"
    assert params["html"] == "true"
    assert params["markdown"] == "true"
    assert params["screenshot"] == "true"
    assert params["browserRendering"] == "true"
    assert params["waitUntil"] == "networkidle"
    assert params["maxRetries"] == "3"
    assert params["tokenCap"] == "30"
    await http_client.aclose()


@pytest.mark.asyncio
async def test_public_scraper_api_defaults_to_html_only(recorded_client):
    http_client, requests = recorded_client
    client = MrScraper("test-token", http_client=http_client)

    await client.scraper_api("https://example.com")

    params = requests[0].url.params
    assert params["html"] == "true"
    assert params["markdown"] == "false"
    assert "screenshot" not in params
    assert "browserRendering" not in params
    await http_client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kwargs",
    [
        {"html": False},
        {"html": False, "markdown": False, "screenshot": False},
        {"html": "yes"},
        {"screenshot": "full"},
    ],
)
async def test_public_scraper_api_rejects_invalid_outputs(recorded_client, kwargs):
    http_client, requests = recorded_client
    client = MrScraper("test-token", http_client=http_client)

    with pytest.raises(ValueError):
        await client.scraper_api("https://example.com", **kwargs)

    assert requests == []
    await http_client.aclose()


@pytest.mark.asyncio
async def test_web_search_posts_websearch_action(recorded_client):
    http_client, requests = recorded_client
    client = MrScraper("test-token", http_client=http_client)

    await client.web_search(" e-menessaptieka.lv linkedin ", country="us", num_results=25)

    request = requests[0]
    assert request.method == "POST"
    assert request.url.host == "api.mrscraper.com"
    assert request.url.path == "/"
    assert not request.url.params
    assert request.headers["x-api-token"] == "test-token"
    assert request_json(request) == {
        "action": "websearch",
        "query": "e-menessaptieka.lv linkedin",
        "country": "us",
        "numResults": 25,
    }
    await http_client.aclose()


@pytest.mark.asyncio
async def test_web_search_defaults(recorded_client):
    http_client, requests = recorded_client
    client = MrScraper("test-token", http_client=http_client)

    await client.web_search("python web scraping")

    assert request_json(requests[0]) == {
        "action": "websearch",
        "query": "python web scraping",
        "numResults": 10,
    }
    await http_client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query,kwargs",
    [
        ("", {}),
        ("   ", {}),
        ("python", {"num_results": 9}),
        ("python", {"num_results": 101}),
        ("python", {"num_results": 15.5}),
        ("python", {"num_results": True}),
        ("python", {"country": ""}),
        ("python", {"timeout": 0}),
    ],
)
async def test_web_search_rejects_invalid_input_before_request(recorded_client, query, kwargs):
    http_client, requests = recorded_client
    client = MrScraper("test-token", http_client=http_client)

    with pytest.raises(ValueError):
        await client.web_search(query, **kwargs)

    assert requests == []
    await http_client.aclose()
