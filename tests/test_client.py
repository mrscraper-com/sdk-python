"""Unit tests for request construction and backward-compatible SDK features."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from mrscraper import MrScraper


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
async def test_fetch_html_supports_cli_controls(recorded_client):
    http_client, requests = recorded_client
    client = MrScraper("test-token", http_client=http_client)

    await client.fetch_html(
        "https://example.com/page",
        timeout=45,
        geo_code="ID",
        browser_rendering=True,
        super_mode=True,
        wait_for_selector=".ready",
        home_page=True,
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
    assert payload["url"] == "https://example.com/page"
    assert payload["browserRendering"] is True
    assert payload["super"] is True
    assert payload["geoCode"] == "ID"
    assert payload["waitForSelector"] == ".ready"
    assert payload["homePage"] is True
    assert payload["blockResources"] is True
    assert payload["maxRetries"] == 4
    assert payload["tokenCap"] == 100
    assert payload["useProxy"] is False
    assert payload["proxy"] == "user:pass@proxy.example:8000"
    assert payload["proxyCountry"] == "SG"
    assert payload["bypassProxy"] is True
    assert payload["cookieJar"].startswith("domain=example.com")
    assert payload["headers"] == {"accept-language": "en-US"}
    assert payload["stream"] is True
    assert payload["token"] == "test-token"
    assert request.headers["authorization"] == "Bearer test-token"
    assert request.headers["x-api-token"] == "test-token"
    assert request.headers["x-discard-token-secret"] == "discard-secret"
    assert not http_client.is_closed
    await http_client.aclose()


@pytest.mark.asyncio
async def test_fetch_google_serp_uses_v2_and_normalizes_google_url(recorded_client):
    http_client, requests = recorded_client
    client = MrScraper("test-token", http_client=http_client)

    await client.fetch_google_serp(
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
async def test_fetch_google_serp_keeps_raw_compatibility(recorded_client):
    http_client, requests = recorded_client
    client = MrScraper("test-token", http_client=http_client)

    await client.fetch_google_serp("iphone 17")

    assert request_json(requests[0]) == {
        "query": "iphone 17",
        "format": "html",
        "renderJs": False,
    }
    await http_client.aclose()


@pytest.mark.asyncio
async def test_create_scraper_adds_mode_schema_and_listing_pages(recorded_client):
    http_client, requests = recorded_client
    client = MrScraper("test-token", http_client=http_client)

    await client.create_scraper(
        "https://example.com/products",
        "Extract products",
        agent="listing",
        mode="Super",
        schema_prompt={"type": "array"},
        max_pages=4,
    )

    payload = request_json(requests[0])
    assert payload["mode"] == "Super"
    assert payload["maxPages"] == 4
    assert '"type": "array"' in payload["message"]
    assert "proxyCountry" not in payload
    await http_client.aclose()


@pytest.mark.asyncio
async def test_rerun_results_and_result_add_cli_controls(recorded_client):
    http_client, requests = recorded_client
    client = MrScraper("test-token", http_client=http_client)

    await client.rerun_scraper(
        "scraper-1",
        "https://example.com",
        proxy_country="ID",
        max_retries=4,
        timeout=120,
        home_page=True,
        html=True,
        markdown=True,
        screenshot=True,
        bypass_proxy=True,
        wait_for_selector=".ready",
        render_javascript=True,
        use_proxy=False,
        proxy="user:pass@proxy.example:8000",
        return_cookies=True,
        show_modal=True,
        stream=True,
    )
    await client.get_all_results(
        scraper_id="scraper-1",
        status="Finished",
        type="Rerun-AI",
        url="https://example.com/?page=2",
    )
    await client.get_result_by_id("result-1", include_html=False)

    rerun_payload = request_json(requests[0])
    assert rerun_payload["proxyCountry"] == "ID"
    assert rerun_payload["maxRetry"] == 4
    assert rerun_payload["timeout"] == 120
    assert rerun_payload["useHomePage"] is True
    assert rerun_payload["html"] is True
    assert rerun_payload["markdown"] is True
    assert rerun_payload["screenshot"] is True
    assert rerun_payload["bypassProxy"] is True
    assert rerun_payload["waitForSelector"] == ".ready"
    assert rerun_payload["renderJavascript"] is True
    assert rerun_payload["useProxy"] is False
    assert rerun_payload["proxy"] == "user:pass@proxy.example:8000"
    assert rerun_payload["returnCookies"] is True
    assert rerun_payload["showModal"] is True
    assert rerun_payload["stream"] is True
    assert requests[1].url.params["filters[scraperId]"] == "scraper-1"
    assert requests[1].url.params["filters[status]"] == "Finished"
    assert requests[1].url.params["filters[type]"] == "Rerun-AI"
    assert requests[1].url.params["filters[url]"] == "https://example.com/?page=2"
    assert requests[2].url.params["includeHtml"] == "false"
    await http_client.aclose()


@pytest.mark.asyncio
async def test_rerun_manual_scraper_adds_browser_and_proxy_controls(recorded_client):
    http_client, requests = recorded_client
    client = MrScraper("test-token", http_client=http_client)

    await client.rerun_manual_scraper(
        "manual-1",
        "https://example.com",
        proxy="user:pass@proxy.example:8000",
        proxy_country="ID",
        max_retries=5,
        return_cookies=True,
        global_domain=False,
        use_proxy=False,
        bypass_proxy=False,
        home_page=True,
        home_page_timeout=20,
        html=True,
        markdown=True,
        screenshot="full",
        cookie_jar="domain=example.com&country=id",
        browser_flags={"headless": True},
        token_cap=200,
        stream=True,
    )

    payload = request_json(requests[0])
    assert payload == {
        "scraperId": "manual-1",
        "url": "https://example.com",
        "proxy": "user:pass@proxy.example:8000",
        "proxyCountry": "ID",
        "maxRetry": 5,
        "maxRetries": 5,
        "returnCookie": True,
        "globalDomain": False,
        "useProxy": False,
        "bypassProxy": False,
        "homePage": True,
        "homePageTimeout": 20,
        "html": True,
        "markdown": True,
        "screenshot": "full",
        "cookieJar": "domain=example.com&country=id",
        "browserFlags": {"headless": True},
        "tokenCap": 200,
        "stream": True,
    }
    await http_client.aclose()


@pytest.mark.asyncio
async def test_account_and_analytics_methods(recorded_client):
    http_client, requests = recorded_client
    client = MrScraper("test-token", http_client=http_client)

    await client.get_subscription_account()
    await client.get_analytic_statuses(
        "example.com",
        "2026-09-01 00:00:00",
        "2026-09-07 00:00:00",
        action="fetch",
        api_token_name="production",
    )

    assert requests[0].url.path == "/api/v1/subscription-accounts"
    assert requests[1].url.path == "/api/v1/analytic/statuses"
    assert requests[1].url.params["domain"] == "example.com"
    assert requests[1].url.params["action"] == "fetch"
    assert requests[1].url.params["apiTokenName"] == "production"
    await http_client.aclose()
