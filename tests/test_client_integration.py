"""
Integration tests for the two MrScraper services against the real API.

These tests make real HTTP requests to api.mrscraper.com and sync.scraper.mrscraper.com.
All API responses are automatically saved into debug_results/*.json
"""

from __future__ import annotations

import os
import json
import pytest
from datetime import datetime

from mrscraper import MrScraper
from mrscraper.exceptions import AuthenticationError

REAL_TOKEN = os.environ.get("MRSCRAPER_TOKEN", "")
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
class TestFetchHtmlReal:
    async def test_scraper_api_returns_200_and_html(self, client):
        result = await client.scraper_api("https://books.toscrape.com/")
        save_result("scraper_api_basic", result)

        assert isinstance(result, dict)
        assert result["status_code"] == 200
        assert "data" in result
        assert "<html" in result["data"].lower()

    async def test_scraper_api_respects_geo_code(self, client):
        result = await client.scraper_api(
            "https://books.toscrape.com/",
            geo_code="US",
        )
        save_result("scraper_api_geo_us", result)

        assert isinstance(result, dict)
        assert result["status_code"] == 200
        assert "data" in result


@pytest.mark.integration
@pytest.mark.asyncio
class TestFetchGoogleSerpReal:
    async def test_web_search_returns_data(self, client):
        result = await client.web_search(
            "https://www.google.com/search?q=iphone+17",
            raw=True,
        )
        save_result("web_search", result)

        assert isinstance(result, dict)
        assert result["status_code"] == 200
        assert "data" in result


@pytest.mark.integration
@pytest.mark.asyncio
class TestInvalidToken:
    async def test_invalid_token_raises_authentication_error(self):
        client = MrScraper("INVALID_MRSCRAPER_API_TOKEN")
        with pytest.raises(AuthenticationError):
            await client.scraper_api("https://books.toscrape.com/")
