"""
Integration tests for the public MrScraper methods against the real API.

These tests make real HTTP requests to api.mrscraper.com.
All API responses are automatically saved into debug_results/*.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import pytest

from mrscraper import MrScraper
from mrscraper.exceptions import AuthenticationError

REAL_TOKEN = os.environ.get("MRSCRAPER_TOKEN") or os.environ.get("MRSCRAPER_API_TOKEN", "")
DEBUG_DIR = os.environ.get(
    "MRSCRAPER_DEBUG_DIR",
    os.path.join(os.path.dirname(__file__), "debug_results"),
)


def save_result(test_name: str, result: dict):
    os.makedirs(DEBUG_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{test_name}_{timestamp}.json"
    filepath = os.path.join(DEBUG_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)

    print(f"\nSaved result to: {os.path.abspath(filepath)}\n")


@pytest.fixture(scope="module")
def token():
    if not REAL_TOKEN or REAL_TOKEN == "<YOUR_REAL_TOKEN>":
        pytest.skip("Set MRSCRAPER_TOKEN env var to run integration tests.")
    return REAL_TOKEN


@pytest.fixture
def client(token):
    return MrScraper(token)


@pytest.mark.integration
@pytest.mark.asyncio
class TestScraperApiReal:
    async def test_scraper_api_returns_200_and_html(self, client):
        result = await client.scraper_api("https://books.toscrape.com/")
        save_result("scraper_api_basic", result)

        assert isinstance(result, dict)
        assert result["status_code"] == 200
        assert "data" in result
        assert "<html" in result["data"].lower()

    async def test_scraper_api_returns_combined_outputs(self, client):
        result = await client.scraper_api(
            "https://books.toscrape.com/",
            html=True,
            markdown=True,
            geo_code="US",
        )
        save_result("scraper_api_html_markdown", result)

        assert result["status_code"] == 200
        assert "<html" in result["data"]["html"].lower()
        assert result["data"]["markdown"]


@pytest.mark.integration
@pytest.mark.asyncio
class TestWebSearchReal:
    async def test_web_search_returns_results(self, client):
        result = await client.web_search(
            "e-menessaptieka.lv linkedin",
            country="us",
            num_results=10,
        )
        save_result("web_search", result)

        assert result["status_code"] == 200
        assert result["data"]["success"] is True
        first = result["data"]["data"][0]
        assert {"rank", "title", "url", "description"} <= first.keys()


@pytest.mark.integration
@pytest.mark.asyncio
class TestAccountReal:
    async def test_account_returns_summary(self, client):
        result = await client.account()

        assert result["status_code"] == 200
        assert "token_remaining" in result["data"]


@pytest.mark.integration
@pytest.mark.asyncio
class TestInvalidToken:
    async def test_invalid_token_raises_authentication_error(self):
        client = MrScraper("INVALID_MRSCRAPER_API_TOKEN")
        with pytest.raises(AuthenticationError):
            await client.scraper_api("https://books.toscrape.com/")
