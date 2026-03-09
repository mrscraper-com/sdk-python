"""
MrScraper Python SDK

A clean Python client for the `MrScraper <https://mrscraper.com>`_ API.
Supports async/await usage.

Quickstart::

    import asyncio
    from mrscraper import MrScraper

    async def main():
        client = MrScraper(token="atk_your_token_here")
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
