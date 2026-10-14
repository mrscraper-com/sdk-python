"""
MrScraper Python SDK

A clean Python client for the `MrScraper <https://mrscraper.com>`_ API.
Supports async/await usage.

Quickstart::

    import asyncio
    from mrscraper import MrScraper

    async def main():
        client = MrScraper(token="MRSCRAPER_API_TOKEN")
        result = await client.scraper_api("https://example.com")
        print(result["data"])

    asyncio.run(main())
"""

from .exceptions import APIError, AuthenticationError, MrScraperError, NetworkError
from .mrscraper import MrScraper

__all__ = [
    "MrScraper",
    "MrScraperError",
    "AuthenticationError",
    "APIError",
    "NetworkError",
]

__version__ = "0.6.0"
