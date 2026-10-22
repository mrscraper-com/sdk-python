"""Checks shared by the local smoke-test runners.

The developer-only runner is not included in source distributions.
"""

import json

import httpx
import pytest

from mrscraper import MrScraper

smoke_test = pytest.importorskip("file", reason="Local smoke runner is not shipped in the sdist")


@pytest.mark.asyncio
async def test_account_command_checks_subscription():
    async def handler(request):
        assert request.method == "GET"
        assert request.url.path == "/api/v1/subscription-accounts"
        return httpx.Response(200, json={"data": {"tokenLimit": 100, "tokenUsage": 20}})

    args = smoke_test.build_parser().parse_args(["account"])
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        result = await smoke_test.run_method(MrScraper("test-token", http_client=http_client), args)
    assert result["data"]["token_remaining"] == 80


@pytest.mark.asyncio
async def test_web_search_command_calls_renamed_method():
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"ok": True})

    args = smoke_test.build_parser().parse_args(["google-serp", "--query", "python web scraping"])
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        await smoke_test.run_method(MrScraper("test-token", http_client=http_client), args)

    assert requests[0].url.path == "/api/google/serp/v2/sync"
    assert json.loads(requests[0].content)["query"] == "python web scraping"
