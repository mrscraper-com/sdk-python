"""
MrScraper Python SDK

A clean Python client for the `MrScraper <https://mrscraper.com>`_ API.

Quickstart (sync)::

    from mrscraper import MrScraperClient

    client = MrScraperClient(token="atk_your_token_here")

    # Fetch rendered HTML
    result = client.fetch_html("https://example.com")
    print(result["data"])

    # Create an AI scraper
    scraper = client.create_scraper(
        "https://example.com/products",
        "Extract all product names and prices",
    )

Quickstart (async)::

    import asyncio
    from mrscraper import AsyncMrScraperClient

    async def main():
        client = AsyncMrScraperClient(token="atk_your_token_here")
        result = await client.fetch_html("https://example.com")
        print(result["data"])

    asyncio.run(main())
"""

from .mrscraper import MrScraper
from .exceptions import APIError, AuthenticationError, MrScraperError, NetworkError

__all__ = [
    "MrScraper",
    "MrScraperError",
    "AuthenticationError",
    "APIError",
    "NetworkError",
]

__version__ = "0.1.0"
