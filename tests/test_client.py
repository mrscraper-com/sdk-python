"""Contract checks derived from CLI lib/api.js; no live requests."""

import json

import httpx
import pytest

from mrscraper import APIError, AuthenticationError, MrScraper, NetworkError

URL = "https://example.com/page?a=1&b=two"
SERVICES = (
    "status",
    "scrape_html",
    "scrape_markdown",
    "get_screenshot",
    "scrape_brand",
    "scrape_json",
    "web_search",
)


def test_public_services():
    assert {
        name for name, fn in vars(MrScraper).items() if not name.startswith("_") and callable(fn)
    } == set(SERVICES)


@pytest.mark.parametrize("name", SERVICES)
async def test_service_contract(recorded, name):
    client, calls = recorded
    args = () if name == "status" else ("  web scraping  " if name == "web_search" else URL,)
    result = await getattr(client, name)(*args)
    req = calls[0]
    assert req.method == "GET"
    assert not req.content
    assert req.headers["authorization"] == "Bearer test-token"
    assert req.headers["x-api-token"] == "test-token"
    assert "token" not in req.url.params
    assert result["status_code"] == 200
    params = dict(req.url.params)
    if name == "status":
        assert req.url.path == "/api/v1/subscription-accounts"
        assert req.extensions["timeout"]["read"] == 600
        return
    assert req.url.host == "api.mrscraper.com"
    if name == "scrape_brand":
        expected_brand = {"action": "brand-scraping", "url": URL, "bundle": "none"}
        assert params == expected_brand
        assert list(params) == list(expected_brand)
        assert req.extensions["timeout"]["read"] == 120
        return
    if name == "web_search":
        assert req.extensions["timeout"]["read"] == 120
        assert params == {"action": "websearch", "query": "web scraping", "numResults": "10"}
        return
    # Documented request order: timeout, warmStart, blockResources, then saving and caching.
    loading = {"timeout": "300", "warmStart": "false", "blockResources": "false"}
    saving = {"saveResult": "true", "maxAge": "0"}
    expected = {
        "scrape_html": {
            "url": URL,
            "html": "true",
            "markdown": "false",
            **loading,
            **saving,
            "screenshot": "false",
        },
        "scrape_markdown": {
            "url": URL,
            "markdown": "true",
            "html": "false",
            "screenshot": "false",
            **loading,
            **saving,
        },
        "get_screenshot": {
            "url": URL,
            "screenshot": "full",
            "html": "false",
            "markdown": "false",
            "browserRendering": "true",
            "timeout": "300",
            **saving,
        },
        "scrape_json": {
            "url": URL,
            "prompt": "Extract all data as complete as possible.",
            "agent": "general",
            "html": "true",
            **loading,
            **saving,
            "screenshot": "false",
        },
    }[name]
    assert params == expected
    assert list(params) == list(expected)
    assert req.extensions["timeout"]["read"] == 330


async def test_page_options_map_to_documented_fields_in_order(recorded):
    client, calls = recorded
    shared = {
        "timeout": 330,
        "wait_for_selector": " .ready ",
        "geo_code": "ID",
        "max_age": 604800000,
        "max_retries": 0,
    }
    loading = {"browser_rendering": False, "warm_start": True, "block_resources": True}
    await client.scrape_html(
        URL, **shared, **loading, action=" analytics ", screenshot="1920x1080-75"
    )
    await client.scrape_markdown(URL, **shared, **loading, action="analytics")
    await client.get_screenshot(URL, **shared)
    await client.scrape_json(
        URL, "Extract prices", **shared, **loading, html=False, screenshot=True
    )
    # saveResult is always true and tokenCap is never sent.
    wire_shared = {
        "timeout": "330",
        "waitForSelector": ".ready",
        "geoCode": "id",
        "saveResult": "true",
        "maxAge": "604800000",
        "maxRetries": "0",
    }
    wire_loading = {"browserRendering": "false", "warmStart": "true", "blockResources": "true"}
    html, markdown, screenshot, json_request = (dict(call.url.params) for call in calls)
    assert list(html) == [
        "url",
        "html",
        "markdown",
        "browserRendering",
        "timeout",
        "warmStart",
        "blockResources",
        "waitForSelector",
        "action",
        "geoCode",
        "saveResult",
        "maxAge",
        "maxRetries",
        "screenshot",
    ]
    # A screenshot sends browserRendering=true even when browser_rendering is False.
    assert html == {
        "url": URL,
        "html": "true",
        "markdown": "false",
        **wire_loading,
        "browserRendering": "true",
        "action": "analytics",
        **wire_shared,
        "screenshot": "1920x1080-75",
    }
    assert markdown == {
        "url": URL,
        "markdown": "true",
        "html": "false",
        "screenshot": "false",
        **wire_loading,
        "action": "analytics",
        **wire_shared,
    }
    assert list(screenshot)[:5] == ["url", "screenshot", "html", "markdown", "browserRendering"]
    assert screenshot == {
        "url": URL,
        "screenshot": "full",
        "html": "false",
        "markdown": "false",
        "browserRendering": "true",
        **wire_shared,
    }
    assert json_request == {
        "url": URL,
        "prompt": "Extract prices",
        "agent": "general",
        "html": "false",
        **wire_loading,
        **wire_shared,
        "screenshot": "true",
    }
    assert calls[0].extensions["timeout"]["read"] == 360


async def test_json_short_and_long_prompts(recorded):
    client, calls = recorded
    await client.scrape_json(URL, "  Extract titles  ", max_retries=0)
    await client.scrape_json(URL, "é &" * 4000, max_retries=0)
    assert calls[0].url.params["prompt"] == "  Extract titles  "
    req = calls[1]
    assert req.method == "POST"
    assert json.loads(req.content) == {"url": URL, "prompt": "é &" * 4000, "agent": "general"}
    assert not {"url", "prompt", "agent"}.intersection(req.url.params)
    assert req.url.params["maxRetries"] == "0"
    assert req.url.params["saveResult"] == "true"
    assert req.url.params["html"] == "true"
    assert "token" not in str(req.url)


@pytest.mark.parametrize(
    "status,error", [(401, AuthenticationError), (429, APIError), (500, APIError)]
)
async def test_http_failures(status, error):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(status, json={"error": "failed"}))
    ) as http:
        with pytest.raises(error):
            await MrScraper("test", http_client=http).scrape_html(URL)


async def test_network_failure():
    def fail(req):
        raise httpx.ReadTimeout("timeout", request=req)

    async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as http:
        with pytest.raises(NetworkError):
            await MrScraper("test", http_client=http).scrape_html(URL)


@pytest.mark.parametrize(
    "content_type,data",
    [
        ("text/html", b"<html>test</html>"),
        ("text/markdown", b"# test"),
        ("image/png", b"\x89PNG\x00\xff"),
        ("application/json", b'{"data":{"ok":true}}'),
    ],
)
async def test_response_types(content_type, data):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, content=data, headers={"content-type": content_type})
        )
    ) as http:
        result = await MrScraper("test", http_client=http).get_screenshot(URL)
    assert result["data"] == (
        json.loads(data)
        if content_type == "application/json"
        else data
        if content_type == "image/png"
        else data.decode()
    )
