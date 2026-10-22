"""Public scraping methods produce the API requests shown in the SDK examples."""

from __future__ import annotations

import inspect
import json

import httpx
import pytest

from mrscraper import MrScraper


@pytest.fixture
async def recorded_client():
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"ok": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        yield MrScraper("test-token", http_client=http_client), requests


def payload(request: httpx.Request):
    return json.loads(request.content) if request.content else None


def test_scraper_api_is_internal_and_output_choices_are_not_public_controls():
    assert not hasattr(MrScraper, "scraper_api")
    assert callable(MrScraper._scraper_api)
    for method in (
        "scraper_html", "scraper_markdown", "get_screenshot", "scraper_json",
        "scraper_multiple_page", "scraper_sitemap", "scrape_brand",
    ):
        parameters = inspect.signature(getattr(MrScraper, method)).parameters
        assert not {"html", "markdown", "screenshot"}.intersection(parameters)


@pytest.mark.parametrize("method,output", [("scraper_html", "html"), ("scraper_markdown", "markdown")])
async def test_content_method_requests_only_its_output(recorded_client, method, output):
    client, requests = recorded_client

    result = await getattr(client, method)("https://example.com/page")

    request = requests[0]
    assert request.method == "POST"
    assert request.url.host == "api.mrscraper.com"
    assert request.url.path == "/"
    assert payload(request) == {"url": "https://example.com/page", "maxRetries": 3}
    assert request.url.params[output] == "true"
    for excluded in {"html", "markdown", "screenshot"} - {output}:
        assert excluded not in request.url.params
    assert request.url.params["geoCode"] == "US"
    assert request.url.params["timeout"] == "120"
    assert request.headers["x-api-token"] == "test-token"
    assert result["data"] == {"ok": True}


@pytest.mark.parametrize(
    "method",
    ["scraper_html", "scraper_markdown", "scraper_json", "scraper_multiple_page", "scraper_sitemap", "scrape_brand"],
)
async def test_scraping_methods_forward_shared_controls(recorded_client, method):
    client, requests = recorded_client

    await getattr(client, method)(
        "https://example.com/page",
        timeout=45,
        geo_code="ID",
        proxy_country="SG",
        browser_rendering=True,
        super=True,
        home_page=True,
        block_resources=True,
        max_retries=4,
        token_cap=30,
        use_proxy=False,
        proxy="user:pass@proxy.example:8000",
        wait_for_selector=".ready",
        bypass_proxy=True,
        cookie_jar="domain=example.com&country=sg",
        headers={"accept-language": "en-US"},
        stream=True,
        discard_token_secret="discard-secret",
    )

    request = requests[0]
    params = request.url.params
    assert params["timeout"] == "45"
    assert params["geoCode"] == "ID"
    assert params["proxyCountry"] == "SG"
    assert params["browserRendering"] == "true"
    assert params["super"] == "true"
    assert params["warmStart"] == "true"
    assert params["blockResources"] == "true"
    assert params["useProxy"] == "false"
    assert params["proxy"] == "user:pass@proxy.example:8000"
    assert params["waitForSelector"] == ".ready"
    assert params["bypassProxy"] == "true"
    assert params["cookieJar"] == "domain=example.com&country=sg"
    assert json.loads(params["headers"]) == {"accept-language": "en-US"}
    assert params["stream"] == "true"
    assert request.headers["x-discard-token-secret"] == "discard-secret"
    controls = params if method == "scrape_brand" else payload(request)
    assert str(controls["maxRetries"]) == "4"
    assert str(controls["tokenCap"]) == "30"


@pytest.mark.parametrize("full_page,expected", [(True, "full"), (False, "true")])
async def test_screenshot_uses_get_and_browser_defaults(recorded_client, full_page, expected):
    client, requests = recorded_client

    await client.get_screenshot(
        "https://example.com/page?a=one&b=two", full_page=full_page, token_cap=30,
    )

    request = requests[0]
    assert request.method == "GET"
    assert request.content == b""
    params = request.url.params
    assert params["url"] == "https://example.com/page?a=one&b=two"
    assert params["screenshot"] == expected
    assert params["browserRendering"] == "true"
    assert params["waitUntil"] == "domcontentloaded"
    assert params["timeout"] == "300"
    assert params["maxRetries"] == "3"
    assert params["tokenCap"] == "30"
    assert "html" not in params
    assert "markdown" not in params


async def test_screenshot_supports_wait_controls(recorded_client):
    client, requests = recorded_client

    await client.get_screenshot(
        "https://example.com", wait_until="networkidle", timeout=90, max_retries=0,
    )

    params = requests[0].url.params
    assert params["browserRendering"] == "true"
    assert params["waitUntil"] == "networkidle"
    assert params["timeout"] == "90"
    assert params["maxRetries"] == "0"
    assert "tokenCap" not in params


@pytest.mark.parametrize(
    "method,body,output",
    [
        ("scraper_json", {
            "url": "https://example.com", "maxRetries": 3,
            "prompt": "Extract all data as complete as possible.", "agent": "general",
        }, "html"),
        ("scraper_multiple_page", {
            "url": "https://example.com", "maxRetries": 3,
            "prompt": "Extract all entry data as complete as possible.",
            "agent": "listing", "maxPages": 3,
        }, None),
        ("scraper_sitemap", {
            "url": "https://example.com", "maxRetries": 3,
            "agent": "map", "maxDepth": 2, "maxPages": 3, "limit": 1000,
        }, None),
    ],
)
async def test_agent_methods_have_correct_defaults(recorded_client, method, body, output):
    client, requests = recorded_client

    await getattr(client, method)("https://example.com")

    request = requests[0]
    assert request.method == "POST"
    assert payload(request) == body
    for flag in ("html", "markdown", "screenshot"):
        if flag == output:
            assert request.url.params[flag] == "true"
        else:
            assert flag not in request.url.params


async def test_agent_methods_forward_extraction_controls(recorded_client):
    client, requests = recorded_client

    await client.scraper_json("https://example.com", prompt="Extract prices.")
    await client.scraper_multiple_page("https://example.com", prompt="Extract titles.", max_pages=8)
    await client.scraper_sitemap("https://example.com", max_depth=4, max_pages=10, limit=50)

    assert payload(requests[0])["prompt"] == "Extract prices."
    assert payload(requests[1])["prompt"] == "Extract titles."
    assert payload(requests[1])["maxPages"] == 8
    assert payload(requests[2])["maxDepth"] == 4
    assert payload(requests[2])["maxPages"] == 10
    assert payload(requests[2])["limit"] == 50


@pytest.mark.parametrize(
    "include_patterns,exclude_patterns",
    [
        (r"https://example\.com/docs/.*", r"/(archive|private)/|\?page=\d+"),
        ("", ""),
        (None, None),
    ],
)
async def test_sitemap_preserves_optional_pattern_strings(
    recorded_client, include_patterns, exclude_patterns,
):
    client, requests = recorded_client

    await client.scraper_sitemap(
        "https://example.com", include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
    )

    request = requests[0]
    body = payload(request)
    for name, value in (("includePatterns", include_patterns), ("excludePatterns", exclude_patterns)):
        assert name not in request.url.params
        if value is None:
            assert name not in body
        else:
            assert body[name] == value


@pytest.mark.parametrize("bundle", ["clean", "full", "none"])
async def test_brand_scraping_posts_action_bundle_and_target_url(recorded_client, bundle):
    client, requests = recorded_client

    await client.scrape_brand("https://example.com/brand?a=1&b=2", bundle=bundle)

    request = requests[0]
    assert request.method == "POST"
    assert request.url.params["action"] == "brand-scraping"
    assert request.url.params["bundle"] == bundle
    assert request.url.params["url"] == "https://example.com/brand?a=1&b=2"
    assert payload(request) == {"url": "https://example.com/brand?a=1&b=2"}
    assert not {"html", "markdown", "screenshot"}.intersection(request.url.params)


async def test_brand_scraping_defaults_to_clean_bundle(recorded_client):
    client, requests = recorded_client
    await client.scrape_brand("https://example.com")
    assert requests[0].url.params["bundle"] == "clean"


@pytest.mark.parametrize("output", [None, "html", "bundle", "screenshot", "screenshot_full"])
async def test_get_brand_uses_job_id_and_optional_output(recorded_client, output):
    client, requests = recorded_client

    await client.get_brand("job/123+abc", output=output, timeout=42)

    request = requests[0]
    assert request.method == "GET"
    assert request.url.path == "/neo/brand"
    assert request.url.params["id"] == "job/123+abc"
    assert request.headers["x-api-token"] == "test-token"
    assert request.extensions["timeout"]["read"] == 42
    assert request.content == b""
    if output is None:
        assert "output" not in request.url.params
    else:
        assert request.url.params["output"] == output


@pytest.mark.parametrize(
    "method,kwargs,content_type,content",
    [
        ("get_screenshot", {}, "image/png", b"\x89PNG\r\n\x1a\n\x00\xff"),
        ("get_brand", {"output": "bundle"}, "application/zip", b"PK\x03\x04\x00\xff"),
        ("get_brand", {"output": "screenshot_full"}, "image/jpeg", b"\xff\xd8\xff\x00"),
        ("get_brand", {"output": "html"}, "text/html; charset=utf-8", b"<html>brand</html>"),
    ],
)
async def test_downloads_preserve_binary_data_and_html_text(method, kwargs, content_type, content):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=content, headers={"content-type": content_type})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = MrScraper("test-token", http_client=http_client)
        target = "https://example.com" if method == "get_screenshot" else "job-123"
        result = await getattr(client, method)(target, **kwargs)

    expected = content.decode() if content_type.startswith("text/") else content
    assert result["data"] == expected
    assert result["status_code"] == 200


@pytest.mark.parametrize(
    "method,kwargs",
    [
        ("scrape_brand", {"bundle": "invalid"}),
        ("get_brand", {"output": "invalid"}),
        ("get_brand", {"timeout": 0}),
        ("get_brand", {"timeout": float("nan")}),
    ],
)
async def test_brand_methods_reject_invalid_controls_before_request(recorded_client, method, kwargs):
    client, requests = recorded_client

    with pytest.raises(ValueError):
        await getattr(client, method)("target", **kwargs)

    assert requests == []
