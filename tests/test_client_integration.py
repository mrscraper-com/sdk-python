"""Opt-in live API checks for each service; calls spend quota."""

import os

import pytest

from mrscraper import MrScraper

pytestmark = pytest.mark.integration
SERVICES = (
    "account",
    "scrape_html",
    "scrape_markdown",
    "get_screenshot",
    "scrape_brand",
    "scrape_json",
    "web_search",
)


@pytest.mark.parametrize("name", SERVICES)
async def test_live_service(name):
    if os.getenv("MRSCRAPER_RUN_LIVE") != "1":
        pytest.skip("Set MRSCRAPER_RUN_LIVE=1")
    if not (os.getenv("MRSCRAPER_API_TOKEN") or os.getenv("MRSCRAPER_API_KEY")):
        pytest.skip("Set a token")
    args = (
        ()
        if name == "account"
        else ("web scraping" if name == "web_search" else "https://books.toscrape.com/",)
    )
    result = await getattr(MrScraper(), name)(*args)
    assert result["status_code"] == 200
    assert result["data"] is not None
