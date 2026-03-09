"""
Integration tests for MrScraperClient against the real API.

These tests make real HTTP requests to api.mrscraper.com and api.app.mrscraper.com.
All API responses are automatically saved into debug_results/*.json
"""

from __future__ import annotations

import os
import json
import pytest
from datetime import datetime

from mrscraper import MrScraper
from mrscraper.exceptions import AuthenticationError

REAL_TOKEN = "<YOUR_REAL_TOKEN>"
DEBUG_DIR = "/Users/mrscraper10/Documents/mrscraper-sdk/debug_dir"


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
    if not REAL_TOKEN:
        pytest.skip("Set REAL_TOKEN to run integration tests.")
    return REAL_TOKEN


@pytest.fixture
def client(token):
    return MrScraper(token)


@pytest.mark.integration
@pytest.mark.asyncio
class TestFetchHtmlReal:

    async def test_fetch_html_returns_200_and_html(self, client):
        result = await client.fetch_html("https://books.toscrape.com/")
        save_result("fetch_html_basic", result)

        assert isinstance(result, dict)
        assert result["status_code"] == 200
        assert "data" in result
        assert "<html" in result["data"].lower()


    async def test_fetch_html_respects_geo_code(self, client):
        result = await client.fetch_html(
            "https://books.toscrape.com/",
            geo_code="US",
        )
        save_result("fetch_html_geo_us", result)

        assert isinstance(result, dict)
        assert result["status_code"] == 200
        assert "data" in result


@pytest.mark.integration
@pytest.mark.asyncio
class TestGetAllResultsReal:

    async def test_get_all_results_returns_structure(self, client):
        result = await client.get_all_results(page=1, page_size=5)
        save_result("get_all_results", result)

        assert result["status_code"] == 200
        assert "data" in result


@pytest.mark.integration
@pytest.mark.asyncio
class TestCreateScraperReal:

    async def test_create_scraper_general_returns_id(self, client):
        result = await client.create_scraper(
            "https://books.toscrape.com/",
            "Extract the main heading text only.",
            agent="general",
        )
        save_result("create_scraper_general", result)

        assert result["status_code"] == 200 or result["status_code"] == 201
        assert "data" in result
        assert "id" in result["data"]["data"] or "scraperId" in result["data"]["data"]

@pytest.mark.integration
@pytest.mark.asyncio
class TestRerunScraperReal:
    async def test_rerun_scraper_returns_id(self, client):
        result = await client.rerun_scraper(
            "4bad946a-1165-41e1-b025-6ef413ae3707",
            "https://books.toscrape.com/",
        )
        save_result("rerun_scraper", result)
        assert result["status_code"] == 200 or result["status_code"] == 201
        assert "data" in result
        assert "scraperId" in result["data"]["data"]

@pytest.mark.integration
@pytest.mark.asyncio
class TestInvalidToken:

    async def test_invalid_token_raises_authentication_error(self):
        client = MrScraper("atk_invalid_fake_token")
        with pytest.raises(AuthenticationError):
            await client.fetch_html("https://books.toscrape.com/")


@pytest.mark.integration
@pytest.mark.asyncio
class TestRerunManualScraperReal:
    async def test_rerun_manual_scraper_returns_id(self, client):
        result = await client.rerun_manual_scraper(
            "817dce5f-4530-415b-9317-c2f660b508d3",
            "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        )
        save_result("rerun_manual_scraper", result)
        assert result["status_code"] == 200 or result["status_code"] == 201
        assert "data" in result
        # API returns run/job object at result["data"]["data"]; scraperId is there, not inside nested "data"
        assert "scraperId" in result["data"]["data"]
        assert result["data"]["data"]["scraperId"] == "817dce5f-4530-415b-9317-c2f660b508d3"

@pytest.mark.integration
@pytest.mark.asyncio
class TestGetAllResultsReal:
    async def test_get_all_results_by_id(self, client):
        result = await client.get_result_by_id(result_id="3e08591e-eb94-44f9-8769-e122501df6f4")
        save_result("get_all_results_by_id", result)
        assert result["status_code"] == 200
        assert "data" in result
        assert result["data"]["data"]["id"] == "3e08591e-eb94-44f9-8769-e122501df6f4"


@pytest.mark.integration
@pytest.mark.asyncio
class TestBulkRerunScraperReal:
    async def test_bulk_rerun_scraper_returns_id(self, client):
        result = await client.bulk_rerun_ai_scraper(
            "fdce9744-570b-48a2-8017-8bcaa251eb6f",
            ["https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html", "https://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html"],
        )
        save_result("bulk_rerun_scraper", result)
        assert result["status_code"] == 200 or result["status_code"] == 201
        assert "data" in result
        assert "bulkResultId" in result["data"]["data"]


@pytest.mark.integration
@pytest.mark.asyncio
class TestBulkRerunManualScraperReal:
    async def test_bulk_rerun_manual_scraper_returns_data(self, client):
        result = await client.bulk_rerun_manual_scraper(
            "817dce5f-4530-415b-9317-c2f660b508d3",
            [
                "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
                "https://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html",
            ],
        )
        save_result("bulk_rerun_manual_scraper", result)
        assert result["status_code"] == 200 or result["status_code"] == 201
        assert "data" in result