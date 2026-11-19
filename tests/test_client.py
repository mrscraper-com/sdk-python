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
        assert params == {"action": "brand-scraping", "url": URL, "bundle": "none"}
        assert req.extensions["timeout"]["read"] == 120
        return
    if name == "web_search":
        assert req.extensions["timeout"]["read"] == 120
        assert params == {
            "action": "websearch",
            "query": "web scraping",
            "country": "us",
            "numResults": "10",
        }
        return
    expected = {
        "url": URL,
        "timeout": "300",
        "geoCode": "us",
        "proxyCountry": "us",
        "super": "false",
        "waitUntil": "domcontentloaded",
        "saveResult": "false",
    }
    if name != "scrape_json":
        expected.update(
            blockResources="false",
            returnCookie="false",
            markdown="true" if name == "scrape_markdown" else "false",
        )
    expected.update(
        browserRendering="true" if name == "get_screenshot" else "false",
        html="true" if name in {"scrape_html", "get_screenshot"} else "false",
        screenshot="full" if name == "get_screenshot" else "false",
    )
    if name == "scrape_json":
        expected.update(agent="general", prompt="Extract all data as complete as possible.")
    assert params == expected
    assert req.extensions["timeout"]["read"] == 330


async def test_loading_and_false_zero_options(recorded):
    client, calls = recorded
    await client.scrape_html(
        URL,
        super=True,
        geo_code="ID",
        proxy_country="SG",
        max_retries=0,
        save_result=True,
        proxy="http://example.com",
        wait_until="networkidle2",
        wait_for_selector=".ready",
        return_cookie=True,
        block_resources=True,
        browser_rendering=True,
        timeout=15,
    )
    p = calls[0].url.params
    for key, value in {
        "super": "true",
        "geoCode": "id",
        "proxyCountry": "sg",
        "maxRetries": "0",
        "saveResult": "true",
        "proxy": "http://example.com",
        "waitUntil": "networkidle2",
        "waitForSelector": ".ready",
        "returnCookie": "true",
        "blockResources": "true",
        "browserRendering": "true",
        "timeout": "15",
    }.items():
        assert p[key] == value
    assert calls[0].extensions["timeout"]["read"] == 45


async def test_json_short_and_long_prompts(recorded):
    client, calls = recorded
    await client.scrape_json(URL, "  Extract titles  ", max_retries=0)
    await client.scrape_json(URL, "é &" * 4000, max_retries=0, save_result=True)
    assert calls[0].url.params["prompt"] == "  Extract titles  "
    req = calls[1]
    assert req.method == "POST"
    assert json.loads(req.content) == {"url": URL, "prompt": "é &" * 4000, "agent": "general"}
    assert not {"url", "prompt", "agent", "blockResources", "returnCookie"}.intersection(
        req.url.params
    )
    assert req.url.params["maxRetries"] == "0"
    assert req.url.params["saveResult"] == "true"
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
