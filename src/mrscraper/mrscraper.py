"""Async client for the MrScraper API."""

from __future__ import annotations

from typing import Any, Literal
from urllib.parse import urlencode

import httpx

from .exceptions import APIError, AuthenticationError, NetworkError

_FETCH_BASE_URL = "https://api.mrscraper.com"
_API_BASE_URL = "https://api.app.mrscraper.com/api/v1"
_SYNC_BASE_URL = "https://sync.scraper.mrscraper.com"

_DEFAULT_TIMEOUT = 120


class MrScraper:
    """
    Async client for the MrScraper API.

    All methods are coroutines and must be awaited.

    Args:
        token: Your MrScraper API token.  Get yours at https://app.mrscraper.com.
        http_client: Optional custom ``httpx.AsyncClient`` instance.  If not
            provided a new one is created per request.

    Example::

        import asyncio
        from mrscraper import AsyncMrScraper

        async def main():
            client = AsyncMrScraper(token="MRSCRAPER_API_TOKEN")
            html = await client.fetch_html("https://example.com")
            print(html["data"])

        asyncio.run(main())
    """

    def __init__(
        self,
        token: str,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._token = token
        self._http_client = http_client

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "accept": "application/json",
            "x-api-token": self._token,
        }

    def _bearer_auth_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "accept": "application/json",
            "Authorization": f"Bearer {self._token}",
        }

    def _client(self) -> httpx.AsyncClient:
        if self._http_client is not None:
            return self._http_client
        return httpx.AsyncClient()

    async def _get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: float = float(_DEFAULT_TIMEOUT + 30),
    ) -> dict[str, Any]:
        async with self._client() as client:
            try:
                response = await client.get(url, headers=headers, timeout=timeout)
                response.raise_for_status()
                return self._parse(response)
            except httpx.HTTPStatusError as exc:
                self._raise_for_status(exc)
                raise  # unreachable; satisfies type checker
            except httpx.HTTPError as exc:
                raise NetworkError(str(exc)) from exc

    async def _post(
        self,
        url: str,
        *,
        payload: dict[str, Any],
        timeout: float = 600.0,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        async with self._client() as client:
            try:
                response = await client.post(
                    url,
                    headers=headers or self._auth_headers(),
                    json=payload,
                    timeout=timeout,
                )
                response.raise_for_status()
                return self._parse(response)
            except httpx.HTTPStatusError as exc:
                self._raise_for_status(exc)
                raise  # unreachable; satisfies type checker
            except httpx.HTTPError as exc:
                raise NetworkError(str(exc)) from exc

    @staticmethod
    def _parse(response: httpx.Response) -> dict[str, Any]:
        if response.status_code == 401:
            raise AuthenticationError(
                "Unauthorized or invalid token. "
                "Please go to https://app.mrscraper.com to get your token."
            )

        content_type = response.headers.get("content-type", "").lower()
        data: Any = response.json() if "application/json" in content_type else response.text
        return {
            "status_code": response.status_code,
            "data": data,
            "headers": dict(response.headers),
        }

    @staticmethod
    def _raise_for_status(exc: httpx.HTTPStatusError) -> None:
        status_code = exc.response.status_code
        if status_code == 401:
            raise AuthenticationError(
                "Unauthorized or invalid token. "
                "Please go to https://app.mrscraper.com to get your token."
            ) from exc
        raise APIError(str(exc), status_code=status_code) from exc

    async def fetch_html(
        self,
        url: str,
        *,
        timeout: int = _DEFAULT_TIMEOUT,
        geo_code: str = "US",
        block_resources: bool = False,
    ) -> dict[str, Any]:
        """
        Fetch the rendered HTML of a page via the MrScraper stealth browser.

        The service handles JavaScript rendering, bot detection evasion, and
        optional geolocation proxying for you.

        Args:
            url: Target URL to scrape (e.g. ``"https://example.com/page"``).
            timeout: Maximum seconds to wait for the page to load (default 120).
            geo_code: ISO country code for proxy-based geolocation (default ``"US"``).
                      Examples: ``"US"``, ``"GB"``, ``"ID"``, ``"SG"``.
            block_resources: When ``True``, images, CSS, and fonts are blocked to
                             speed up the request (default ``False``).

        Returns:
            A dict with keys ``status_code``, ``data`` (raw HTML or JSON), and
            ``headers``.

        Raises:
            AuthenticationError: If the API token is invalid.
            APIError: If the API returns a non-2xx error.
            NetworkError: If a connection or timeout error occurs.

        Example::

            result = await client.fetch_html(
                "https://stockx.com/air-jordan-1-retro-low-og-chicago-2025",
                geo_code="US",
                timeout=120,
            )
            print(result["data"])  # raw HTML string
        """
        params = {
            "token": self._token,
            "timeout": timeout,
            "geoCode": geo_code,
            "url": url,
            "blockResources": str(block_resources).lower(),
        }
        full_url = f"{_FETCH_BASE_URL}?{urlencode(params)}"
        return await self._get(full_url, timeout=float(timeout + 30))

    async def fetch_google_serp(
        self,
        url: str,
        *,
        raw: bool = True,
        timeout: float = 600.0,
    ) -> dict[str, Any]:
        """
        Fetch Google search results (SERP) synchronously.

        Args:
            url: Full Google search URL to scrape
                 (e.g. ``"https://www.google.com/search?q=iphone+17"``).
            raw: When ``True``, return the raw SERP payload (default ``True``).
            timeout: Maximum seconds to wait for the request (default 600).

        Returns:
            A dict with keys ``status_code``, ``data``, and ``headers``.

        Raises:
            AuthenticationError: If the API token is invalid.
            APIError: If the API returns a non-2xx error.
            NetworkError: If a connection or timeout error occurs.

        Example::

            result = await client.fetch_google_serp(
                "https://www.google.com/search?q=iphone+17",
                raw=True,
            )
            print(result["data"])
        """
        endpoint = f"{_SYNC_BASE_URL}/api/google/serp/sync"
        payload: dict[str, Any] = {
            "url": url,
            "raw": raw,
        }
        return await self._post(
            endpoint,
            payload=payload,
            headers=self._bearer_auth_headers(),
            timeout=timeout,
        )

    async def create_scraper(
        self,
        url: str,
        message: str,
        *,
        agent: Literal["general", "listing", "map"] = "general",
        proxy_country: str | None = None,
        max_depth: int = 2,
        max_pages: int = 50,
        limit: int = 1000,
        include_patterns: str = "",
        exclude_patterns: str = "",
    ) -> dict[str, Any]:
        """
        Create an AI-powered scraper and run it immediately.

        The scraper uses natural-language instructions to understand the page
        structure and extract the requested data automatically — no CSS
        selectors required.

        Args:
            url: Target URL to scrape.
            message: Natural-language description of what to extract.
                     Examples: ``"Extract all product names and prices"``,
                     ``"Get article titles and publication dates"``.
            agent: AI agent type (default ``"general"``).

                   * ``"general"`` — works on almost any page; best default.
                   * ``"listing"`` — optimised for listing/grid pages.
                   * ``"map"`` — crawls all sub-pages of a site.
            proxy_country: ISO country code for proxy selection (optional).
                           Examples: ``"US"``, ``"GB"``, ``"SG"``.
            max_depth: *(map agent only)* Crawl depth from the start URL
                       (default 2).  0 = start URL only.
            max_pages: *(map agent only)* Maximum pages to process (default 50).
            limit: *(map agent only)* Maximum records to extract (default 1000).
            include_patterns: *(map agent only)* ``||``-separated URL regex
                              patterns to include when following links.
            exclude_patterns: *(map agent only)* ``||``-separated URL regex
                              patterns to skip when following links.

        Returns:
            A dict with keys ``status_code``, ``data`` (scraper info including
            the scraper ID), and ``headers``.

        Raises:
            AuthenticationError: If the API token is invalid.
            APIError: If the API returns a non-2xx error.
            NetworkError: If a connection or timeout error occurs.

        Example::

            result = await client.create_scraper(
                "https://example.com/products",
                "Extract all product names, prices, and ratings",
                agent="listing",
                proxy_country="US",
            )
            scraper_id = result["data"]["id"]
        """
        endpoint = f"{_API_BASE_URL}/scrapers-ai"

        if agent in ("general", "listing"):
            payload: dict[str, Any] = {
                "url": url,
                "message": message,
                "agent": agent,
                "proxyCountry": proxy_country,
            }
        else:  # map
            payload = {
                "url": url,
                "agent": agent,
                "maxDepth": max_depth,
                "maxPages": max_pages,
                "limit": limit,
                "includePatterns": include_patterns,
                "excludePatterns": exclude_patterns,
            }

        return await self._post(endpoint, payload=payload)

    async def rerun_scraper(
        self,
        scraper_id: str,
        url: str,
        *,
        max_depth: int = 2,
        max_pages: int = 50,
        limit: int = 1000,
        include_patterns: str = "",
        exclude_patterns: str = "",
    ) -> dict[str, Any]:
        """
        Rerun an existing AI scraper on a (new) URL.

        This lets you reuse the extraction logic from a previously created
        scraper on any compatible URL.

        Args:
            scraper_id: ID of the scraper to rerun (from :meth:`create_scraper`).
            url: Target URL.  Can be the original URL or a different page.
            max_depth: *(map agent only)* Crawl depth (default 2).
            max_pages: *(map agent only)* Maximum pages (default 50).
            limit: *(map agent only)* Maximum records (default 1000).
            include_patterns: *(map agent only)* ``||``-separated include patterns.
            exclude_patterns: *(map agent only)* ``||``-separated exclude patterns.

        Returns:
            A dict with keys ``status_code``, ``data``, and ``headers``.

        Raises:
            AuthenticationError: If the API token is invalid.
            APIError: If the API returns a non-2xx error.
            NetworkError: If a connection or timeout error occurs.

        Example::

            result = await client.rerun_scraper(
                scraper_id="scraper_12345",
                url="https://example.com/category/electronics",
                max_depth=3,
                max_pages=100,
            )
        """
        endpoint = f"{_API_BASE_URL}/scrapers-ai-rerun"
        payload: dict[str, Any] = {
            "scraperId": scraper_id,
            "url": url,
            "maxDepth": max_depth,
            "maxPages": max_pages,
            "limit": limit,
            "includePatterns": include_patterns,
            "excludePatterns": exclude_patterns,
        }
        return await self._post(endpoint, payload=payload)

    async def bulk_rerun_ai_scraper(
        self,
        scraper_id: str,
        urls: list[str],
    ) -> dict[str, Any]:
        """
        Rerun an existing AI scraper on multiple URLs in a single batch request.

        More efficient than calling :meth:`rerun_scraper` in a loop because all
        URLs are dispatched in parallel server-side.

        Args:
            scraper_id: ID of the scraper to rerun (from :meth:`create_scraper`).
            urls: List of target URLs.  Must contain at least one URL.

        Returns:
            A dict with keys ``status_code``, ``data``, and ``headers``.

        Raises:
            AuthenticationError: If the API token is invalid.
            APIError: If the API returns a non-2xx error.
            NetworkError: If a connection or timeout error occurs.

        Example::

            result = await client.bulk_rerun_ai_scraper(
                scraper_id="scraper_12345",
                urls=[
                    "https://example.com/products/item1",
                    "https://example.com/products/item2",
                ],
            )
        """
        endpoint = f"{_API_BASE_URL}/scrapers-ai-rerun/bulk"
        payload: dict[str, Any] = {
            "scraperId": scraper_id,
            "urls": urls,
        }
        return await self._post(endpoint, payload=payload)

    async def rerun_manual_scraper(
        self,
        scraper_id: str,
        url: str,
    ) -> dict[str, Any]:
        """
        Rerun a manually configured scraper (created via the MrScraper dashboard)
        on a new URL.

        Use this for scrapers built with custom CSS selectors or XPath rules, not
        for AI scrapers created with :meth:`create_scraper`.

        Args:
            scraper_id: ID of the manual scraper (found in the MrScraper dashboard).
            url: Target URL.  The page structure should match the original scraper's
                 target for selectors to work correctly.

        Returns:
            A dict with keys ``status_code``, ``data``, and ``headers``.

        Raises:
            AuthenticationError: If the API token is invalid.
            APIError: If the API returns a non-2xx error.
            NetworkError: If a connection or timeout error occurs.

        Example::

            result = await client.rerun_manual_scraper(
                scraper_id="manual_scraper_67890",
                url="https://example.com/products/new-item",
            )
        """
        endpoint = f"{_API_BASE_URL}/scrapers-manual-rerun"
        payload: dict[str, Any] = {
            "scraperId": scraper_id,
            "url": url,
        }
        return await self._post(endpoint, payload=payload)

    async def bulk_rerun_manual_scraper(
        self,
        scraper_id: str,
        urls: list[str],
    ) -> dict[str, Any]:
        """
        Rerun a manually configured scraper on multiple URLs in a single batch.

        More efficient than calling :meth:`rerun_manual_scraper` multiple times,
        as all URLs are processed in parallel server-side. Ideal for scraping
        multiple pages, products, or articles with the same extraction logic.

        Args:
            scraper_id: ID of the manual scraper (from the MrScraper dashboard).
                        Must be a scraper created manually via the web interface,
                        not an AI scraper. Find it at https://app.mrscraper.com.
            urls: List of target URLs to scrape. Must contain at least one URL.
                  Each URL is processed independently using the scraper's logic.
                  Example: ``["https://example.com/page1", "https://example.com/page2"]``.

        Returns:
            A dict with keys ``status_code``, ``data`` (bulk job info including job ID,
            status, metadata; use :meth:`get_all_results` or :meth:`get_result_by_id`
            to fetch per-URL results), and ``headers``.

        Raises:
            AuthenticationError: If the API token is invalid.
            APIError: If the API returns a non-2xx error.
            NetworkError: If a connection or timeout error occurs.

        Example::

            result = await client.bulk_rerun_manual_scraper(
                scraper_id="scraper_12345",
                urls=[
                    "https://www.example.com/products/item1",
                    "https://www.example.com/products/item2",
                    "https://www.example.com/products/item3",
                ],
            )
        """
        endpoint = f"{_API_BASE_URL}/scrapers-manual-rerun/bulk"
        payload: dict[str, Any] = {
            "scraperId": scraper_id,
            "urls": urls,
        }
        return await self._post(endpoint, payload=payload, timeout=600.0)

    async def get_all_results(
        self,
        *,
        sort_field: Literal[
            "createdAt",
            "updatedAt",
            "id",
            "type",
            "url",
            "status",
            "error",
            "tokenUsage",
            "runtime",
        ] = "updatedAt",
        sort_order: Literal["ASC", "DESC"] = "DESC",
        page_size: int = 10,
        page: int = 1,
        search: str | None = None,
        date_range_column: str | None = None,
        start_at: str | None = None,
        end_at: str | None = None,
    ) -> dict[str, Any]:
        """
        Retrieve a paginated, sortable, and filterable list of all scraping results.

        Args:
            sort_field: Field to sort by (default ``"updatedAt"``).
                        Options: ``"createdAt"``, ``"updatedAt"``, ``"id"``,
                        ``"type"``, ``"url"``, ``"status"``, ``"error"``,
                        ``"tokenUsage"``, ``"runtime"``.
            sort_order: ``"ASC"`` or ``"DESC"`` (default ``"DESC"``).
            page_size: Results per page (default 10).
            page: Page number, 1-indexed (default 1).
            search: Free-text search query across result fields (optional).
            date_range_column: Column name to filter by date range (optional).
                               Common values: ``"updatedAt"``, ``"createdAt"``.
            start_at: ISO-8601 start date for ``date_range_column`` filter (optional).
                      Example: ``"2024-01-01"`` or ``"2024-01-01T00:00:00"``.
            end_at: ISO-8601 end date for ``date_range_column`` filter (optional).

        Returns:
            A dict with keys ``status_code``, ``data`` (paginated results and
            pagination metadata), and ``headers``.

        Raises:
            AuthenticationError: If the API token is invalid.
            APIError: If the API returns a non-2xx error.
            NetworkError: If a connection or timeout error occurs.

        Example::

            page = await client.get_all_results(
                sort_field="updatedAt",
                sort_order="DESC",
                page_size=20,
                date_range_column="updatedAt",
                start_at="2024-01-01",
                end_at="2024-01-08",
            )
        """
        params: dict[str, Any] = {
            "sortField": sort_field,
            "sortOrder": sort_order,
            "pageSize": page_size,
            "page": page,
        }
        if search is not None:
            params["search"] = search
        if date_range_column is not None:
            params["dateRangeColumn"] = date_range_column
        if start_at is not None:
            params["startAt"] = start_at
        if end_at is not None:
            params["endAt"] = end_at

        url = f"{_API_BASE_URL}/results?{urlencode(params)}"
        return await self._get(url, headers=self._auth_headers(), timeout=600.0)

    async def get_result_by_id(self, result_id: str) -> dict[str, Any]:
        """
        Retrieve full details of a specific scraping result by its ID.

        Args:
            result_id: Unique identifier of the result.  Result IDs are returned
                       by scraper execution methods and by :meth:`get_all_results`.

        Returns:
            A dict with keys ``status_code``, ``data`` (complete result object),
            and ``headers``.

        Raises:
            AuthenticationError: If the API token is invalid.
            APIError: If the API returns a non-2xx error.
            NetworkError: If a connection or timeout error occurs.

        Example::

            result = await client.get_result_by_id("result_12345")
            print(result["data"])
        """
        url = f"{_API_BASE_URL}/results/{result_id}"
        return await self._get(url, headers=self._auth_headers(), timeout=600.0)
