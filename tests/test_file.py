"""Tests for the local smoke-test CLI."""

import json

import httpx
import pytest

import file as smoke_test
from mrscraper import MrScraper


@pytest.mark.asyncio
async def test_scraper_api_super_flag_sets_query_parameter():
    requests = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"ok": True})

    args = smoke_test.build_parser().parse_args(
        ["fetch-content", "--url", "https://example.com", "--super"]
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        await smoke_test.run_method(MrScraper("test-token", http_client=http_client), args)

    assert requests[0].url.params["super"] == "true"


@pytest.mark.asyncio
async def test_scraper_api_without_super_omits_query_parameter():
    requests = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"ok": True})

    args = smoke_test.build_parser().parse_args(["fetch-content", "--url", "https://example.com"])
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        await smoke_test.run_method(MrScraper("test-token", http_client=http_client), args)

    assert "super" not in requests[0].url.params


@pytest.mark.asyncio
async def test_web_search_command_calls_renamed_method():
    requests = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"ok": True})

    args = smoke_test.build_parser().parse_args(
        ["google-serp", "--query", "python web scraping"]
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        await smoke_test.run_method(MrScraper("test-token", http_client=http_client), args)

    assert requests[0].url.path == "/api/google/serp/v2/sync"
    assert json.loads(requests[0].content)["query"] == "python web scraping"
