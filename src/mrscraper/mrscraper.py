"""Async client for the MrScraper API."""

from __future__ import annotations

import json
import os
from typing import Any, Literal
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from .exceptions import APIError, AuthenticationError, NetworkError

_FETCH_BASE_URL = "https://api.mrscraper.com"
_API_BASE_URL = "https://api.app.mrscraper.com/api/v1"
_SYNC_BASE_URL = "https://sync.scraper.mrscraper.com"

_DEFAULT_TIMEOUT = 120

SerpFormat = Literal["json", "html"]
ScrapeMode = Literal["Cheap", "Super"]


class MrScraper:
    """
    Async client for the MrScraper API.

    All methods are coroutines and must be awaited.

    Args:
        token: Your MrScraper API token. If not provided, the client will
            automatically read from the ``MRSCRAPER_API_TOKEN`` environment variable.
            Get yours at https://app.mrscraper.com.
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
        token: str | None = None,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._token = token or os.environ.get("MRSCRAPER_API_TOKEN", "")
        self._http_client = http_client

    def _validate_token(self) -> None:
        if not self._token or not self._token.strip():
            raise AuthenticationError(
                "API token is not set. Please provide a valid token when "
                "initialising the client: MrScraper(token='YOUR_TOKEN'). "
                "Get your token at https://app.mrscraper.com"
            )

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
            "x-api-token": self._token,
        }

    def _client(self) -> httpx.AsyncClient:
        if self._http_client is not None:
            return self._http_client
        return httpx.AsyncClient()

    @staticmethod
    def _compact(values: dict[str, Any]) -> dict[str, Any]:
        """Remove only unset values while preserving ``False``, ``0``, and empty strings."""
        return {key: value for key, value in values.items() if value is not None}

    @staticmethod
    def _normalize_serp_input(value: str) -> tuple[str, str | None, str | None, int | None]:
        """Normalize a query or Google URL into the v2 SERP request fields."""
        value = value.strip()
        if not value:
            raise ValueError("A Google search query or URL is required")

        parsed = urlparse(value)
        if parsed.scheme.lower() in {"http", "https"}:
            params = parse_qs(parsed.query)
            query_values = params.get("q")
            query = query_values[0].strip() if query_values else ""
            if not query:
                raise ValueError("Google search URL must contain a q parameter")
            start_values = params.get("start")
            try:
                start = int(start_values[0]) if start_values else 0
            except ValueError:
                start = 0
            page = start // 10 + 1 if start > 0 else None
            region_values = params.get("gl")
            language_values = params.get("hl")
            return (
                query,
                region_values[0] if region_values else None,
                language_values[0] if language_values else None,
                page,
            )

        return value, None, None, None

    async def _get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: float = float(_DEFAULT_TIMEOUT + 30),
    ) -> dict[str, Any]:
        client = self._client()
        owns_client = self._http_client is None
        try:
            try:
                response = await client.get(url, headers=headers, timeout=timeout)
                response.raise_for_status()
                return self._parse(response)
            except httpx.HTTPStatusError as exc:
                self._raise_for_status(exc)
                raise  # unreachable; satisfies type checker
            except httpx.HTTPError as exc:
                raise NetworkError(str(exc)) from exc
        finally:
            if owns_client:
                await client.aclose()

    async def _post(
        self,
        url: str,
        *,
        payload: dict[str, Any],
        timeout: float = 600.0,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        client = self._client()
        owns_client = self._http_client is None
        try:
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
        finally:
            if owns_client:
                await client.aclose()

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
        html: bool = True,
        markdown: bool = False,
        timeout: int = _DEFAULT_TIMEOUT,
        geo_code: str = "US",
        proxy_country: str | None = None,
        block_resources: bool | None = False,
        browser_rendering: bool | None = None,
        super_mode: bool = False,
        use_proxy: bool = True,
        proxy: str | None = None,
        wait_for_selector: str | None = None,
        home_page: bool = False,
        bypass_proxy: bool = False,
        cookie_jar: str | None = None,
        headers: dict[str, str] | str | None = None,
        max_retries: int = 3,
        token_cap: int | None = None,
        stream: bool | None = None,
        discard_token_secret: str = "",
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
            proxy_country: Compatibility alias sent as ``proxyCountry``.
            block_resources: When ``True``, images, CSS, and fonts are blocked to
                             speed up the request (default ``False``).
            browser_rendering: ``True`` forces browser rendering, ``False`` disables
                               it, and ``None`` lets the API try without a browser
                               before falling back to browser rendering.
            super_mode: Use real-device routing independently of browser rendering.
            use_proxy: Whether the service may use a configured proxy.
            proxy: Custom proxy in ``username:password@host:port`` form.
            wait_for_selector: CSS selector to wait for before returning content.
            home_page: Visit the site's root page before the target URL.
            bypass_proxy: Enable the API's proxy-bypass/resource-blocking behavior.
            cookie_jar: Cookie configuration string, for example
                        ``"domain=example.com&country=us&max_used=100&max_age=50m"``.
            headers: Target request headers as a JSON string or Python dictionary.
            max_retries: Maximum Web Unblocker retries (default 3).
            token_cap: Optional retry-token budget.
            stream: Ask the API for a streamed response. The SDK buffers it into
                    the normal response dictionary.
            discard_token_secret: Optional value sent through the
                                  ``x-discard-token-secret`` request header.

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
        self._validate_token()
        if timeout < 1 or timeout > 300:
            raise ValueError("timeout must be between 1 and 300 seconds")
        if max_retries < 0:
            raise ValueError("max_retries must be greater than or equal to 0")
        if token_cap is not None and token_cap < 0:
            raise ValueError("token_cap must be greater than or equal to 0")
        payload = self._compact(
            {
                "token": self._token,
                "timeout": timeout,
                "geoCode": geo_code,
                "proxyCountry": proxy_country,
                "url": url,
                "browserRendering": browser_rendering,
                "super": super_mode,
                "useProxy": use_proxy,
                "proxy": proxy,
                "html": html,
                "markdown": markdown,
                "waitForSelector": wait_for_selector,
                "homePage": home_page,
                "blockResources": block_resources,
                "bypassProxy": bypass_proxy,
                "cookieJar": cookie_jar,
                "headers": headers,
                "maxRetries": max_retries,
                "tokenCap": token_cap,
                "stream": stream,
            }
        )
        request_headers = self._bearer_auth_headers()
        if discard_token_secret:
            request_headers["x-discard-token-secret"] = discard_token_secret
        return await self._post(
            _FETCH_BASE_URL,
            payload=payload,
            headers=request_headers,
            timeout=float(timeout + 30),
        )

    async def fetch_google_serp(
        self,
        url: str,
        *,
        raw: bool = True,
        region: str | None = None,
        language: str | None = None,
        page: int | None = None,
        format: SerpFormat = "json",
        render_js: bool = False,
        timeout: float = 600.0,
    ) -> dict[str, Any]:
        """
        Fetch Google search results (SERP) synchronously.

        Args:
            url: Google query text or a full Google search URL. The parameter name
                 is retained for backward compatibility.
            raw: Deprecated compatibility alias for ``format="html"``. It takes
                 precedence over ``format`` (default ``True`` for compatibility).
            region: Optional country code. Overrides ``gl`` from a Google URL.
            language: Optional language code. Overrides ``hl`` from a Google URL.
            page: Optional one-based result page. Overrides ``start`` from a URL.
            format: Response representation, ``"json"`` or ``"html"``.
            render_js: Render JavaScript-dependent Google result features.
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
        self._validate_token()
        if format not in ("json", "html"):
            raise ValueError("format must be 'json' or 'html'")
        if page is not None and page < 1:
            raise ValueError("page must be a positive integer")
        query, url_region, url_language, url_page = self._normalize_serp_input(url)
        endpoint = f"{_SYNC_BASE_URL}/api/google/serp/v2/sync"
        payload = self._compact(
            {
                "query": query,
                "region": region or url_region,
                "language": language or url_language,
                "page": page or url_page,
                "format": "html" if raw else format,
                "renderJs": bool(render_js),
            }
        )
        return await self._post(
            endpoint,
            payload=payload,
            headers=self._bearer_auth_headers(),
            timeout=timeout,
        )

    async def create_scraper(
        self,
        url: str,
        message: str | None = None,
        *,
        agent: Literal["general", "listing", "map"] = "general",
        mode: ScrapeMode | None = None,
        schema_prompt: dict[str, Any] | None = None,
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
            mode: Optional backend execution tier, ``"Cheap"`` or ``"Super"``.
            schema_prompt: Optional JSON Schema appended to ``message`` as
                           best-effort output-shape guidance.
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
        self._validate_token()
        endpoint = f"{_API_BASE_URL}/scrapers-ai"

        if agent not in ("general", "listing", "map"):
            raise ValueError("agent must be 'general', 'listing', or 'map'")
        if mode is not None and mode not in ("Cheap", "Super"):
            raise ValueError("mode must be 'Cheap' or 'Super'")

        if agent in ("general", "listing"):
            if not message or not message.strip():
                raise ValueError("message is required for general and listing agents")
            resolved_message = message.strip()
            if schema_prompt is not None:
                resolved_message += (
                    "\n\nBest-effort output guidance: return JSON matching this JSON Schema. "
                    "The MrScraper API does not validate this schema:\n"
                    f"{json.dumps(schema_prompt, indent=2)}"
                )
            payload = self._compact(
                {
                    "url": url,
                    "message": resolved_message,
                    "agent": agent,
                    "mode": mode,
                    "proxyCountry": proxy_country,
                    "maxPages": max_pages if agent == "listing" else None,
                }
            )
        else:  # map
            if message:
                raise ValueError("message is not accepted by the map agent")
            if schema_prompt is not None:
                raise ValueError("schema_prompt is not accepted by the map agent")
            if proxy_country is not None:
                raise ValueError("proxy_country is not accepted by the map agent")
            payload = self._compact(
                {
                    "url": url,
                    "agent": agent,
                    "mode": mode,
                    "maxDepth": max_depth,
                    "maxPages": max_pages,
                    "limit": limit,
                    "includePatterns": include_patterns,
                    "excludePatterns": exclude_patterns,
                }
            )

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
        proxy_country: str | None = None,
        max_retries: int | None = None,
        timeout: int | None = None,
        home_page: bool = False,
        html: bool = False,
        markdown: bool = False,
        screenshot: bool = False,
        bypass_proxy: bool = False,
        wait_for_selector: str | None = None,
        render_javascript: bool = False,
        use_proxy: bool = True,
        proxy: str | None = None,
        return_cookies: bool = False,
        show_modal: bool = False,
        stream: bool = False,
    ) -> dict[str, Any]:
        """
        Rerun an existing AI scraper on a (new) URL.

        This lets you reuse the extraction logic from a previously created
        scraper on any compatible URL.

        Args:
            scraper_id: ID of the scraper to rerun (from :meth:`create_scraper`).
            url: Target URL.  Can be the original URL or a different page.
            max_depth: Map scraper only. Maximum link depth (default 2).
            max_pages: Listing and map scrapers only. Maximum pages (default 50).
            limit: Map scraper only. Maximum discovered results (default 1000).
            include_patterns: Map scraper only. URL inclusion expression.
            exclude_patterns: Map scraper only. URL exclusion expression.
            proxy_country: Optional proxy country code for general/listing scrapers.
            max_retries: Optional maximum retry count.
            timeout: Listing scraper only. Optional backend timeout in seconds.
            home_page: General/listing only. Navigate through the site home page
                       before the target URL.
            html: General/listing only. Include HTML output.
            markdown: General/listing only. Include Markdown output.
            screenshot: General/listing only. Include a screenshot.
            bypass_proxy: General/listing only. Enable proxy bypass/resource blocking.
            wait_for_selector: General/listing only. Wait for this CSS selector.
            render_javascript: General/listing only. Execute page JavaScript.
            use_proxy: General/listing only. Allow proxy use (default ``True``).
            proxy: General/listing only. Optional custom proxy string.
            return_cookies: General/listing only. Include cookies in the result.
            show_modal: General/listing only. Enable modal-related output.
            stream: Listing only. Request streamed processing.

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
        self._validate_token()
        endpoint = f"{_API_BASE_URL}/scrapers-ai-rerun"
        payload = self._compact(
            {
                "scraperId": scraper_id,
                "url": url,
                "maxDepth": max_depth,
                "maxPages": max_pages,
                "limit": limit,
                "includePatterns": include_patterns,
                "excludePatterns": exclude_patterns,
                "proxyCountry": proxy_country,
                "maxRetry": max_retries,
                "timeout": timeout,
                "useHomePage": home_page,
                "html": html,
                "markdown": markdown,
                "screenshot": screenshot,
                "bypassProxy": bypass_proxy,
                "waitForSelector": wait_for_selector,
                "renderJavascript": render_javascript,
                "useProxy": use_proxy,
                "proxy": proxy,
                "returnCookies": return_cookies,
                "showModal": show_modal,
                "stream": stream,
            }
        )
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
        self._validate_token()
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
        *,
        proxy: str | None = None,
        proxy_country: str | None = None,
        max_retries: int = 3,
        return_cookies: bool = False,
        global_domain: bool = True,
        use_proxy: bool = True,
        bypass_proxy: bool = True,
        home_page: bool = False,
        home_page_timeout: int | None = 10,
        html: bool | None = False,
        markdown: bool | None = False,
        screenshot: str | None = None,
        cookie_jar: str | None = None,
        browser_flags: dict[str, Any] | None = None,
        token_cap: int | None = None,
        stream: bool | None = None,
        timeout: float | None = None,
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
            proxy: Optional custom proxy string.
            proxy_country: Optional two-character proxy country code.
            max_retries: Maximum retries for both the rerun service and browser.
            return_cookies: Include cookies in the result.
            global_domain: Apply returned cookies to the global domain.
            use_proxy: Allow proxy use.
            bypass_proxy: Enable proxy bypass/resource blocking.
            home_page: Visit the site home page before the target URL.
            home_page_timeout: Home-page navigation timeout in seconds.
            html: Include HTML output.
            markdown: Include Markdown output.
            screenshot: Optional screenshot mode.
            cookie_jar: Optional cookie configuration string.
            browser_flags: Optional browser configuration dictionary.
            token_cap: Optional retry-token budget.
            stream: Request streamed processing.
            timeout: Optional scraper timeout in seconds.

        Returns:
            A dict with keys ``status_code``, ``data``, and ``headers``.

        Raises:
            AuthenticationError: If the API token is invalid.
            APIError: If the API returns a non-2xx error.
            NetworkError: If a connection or timeout error occurs.

        Example:
            result = await client.rerun_manual_scraper(
                scraper_id="manual_scraper_67890",
                url="https://example.com/products/new-item",
            )

        Warning:
            Scraping login-protected pages carries serious legal and compliance risks. Many websites explicitly prohibit automated access in their Terms of Service, and bypassing authentication to scrape content may expose you to legal action including lawsuits, account termination, and financial penalties. By proceeding on scraping login-protected pages, you confirm that you have read and understood the target website's Terms of Service, and you fully accept all legal, financial, and ethical responsibility for your actions.
        """
        self._validate_token()
        if max_retries < 0:
            raise ValueError("max_retries must be greater than or equal to 0")
        endpoint = f"{_API_BASE_URL}/scrapers-manual-rerun"
        payload = self._compact(
            {
                "scraperId": scraper_id,
                "url": url,
                "proxy": proxy,
                "proxyCountry": proxy_country,
                "maxRetry": max_retries,
                "maxRetries": max_retries,
                "returnCookie": return_cookies,
                "globalDomain": global_domain,
                "useProxy": use_proxy,
                "bypassProxy": bypass_proxy,
                "homePage": home_page,
                "homePageTimeout": home_page_timeout,
                "html": html,
                "markdown": markdown,
                "screenshot": screenshot,
                "cookieJar": cookie_jar,
                "browserFlags": browser_flags,
                "tokenCap": token_cap,
                "stream": stream,
                "timeout": timeout,
            }
        )
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

        Example:
            result = await client.bulk_rerun_manual_scraper(
                scraper_id="scraper_12345",
                urls=[
                    "https://www.example.com/products/item1",
                    "https://www.example.com/products/item2",
                    "https://www.example.com/products/item3",
                ],
            )

        Warning:
            Scraping login-protected pages carries serious legal and compliance risks. Many websites explicitly prohibit automated access in their Terms of Service, and bypassing authentication to scrape content may expose you to legal action including lawsuits, account termination, and financial penalties. By proceeding on scraping login-protected pages, you confirm that you have read and understood the target website's Terms of Service, and you fully accept all legal, financial, and ethical responsibility for your actions.

        """
        self._validate_token()
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
        scraper_id: str | None = None,
        status: str | None = None,
        type: str | None = None,
        url: str | None = None,
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
            scraper_id: Exact saved scraper ID filter.
            status: Exact result status filter.
            type: Exact result type filter.
            url: Exact stored target URL filter.

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
        self._validate_token()
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
        if scraper_id is not None:
            params["filters[scraperId]"] = scraper_id
        if status is not None:
            params["filters[status]"] = status
        if type is not None:
            params["filters[type]"] = type
        if url is not None:
            params["filters[url]"] = url

        url = f"{_API_BASE_URL}/results?{urlencode(params)}"
        return await self._get(url, headers=self._auth_headers(), timeout=600.0)

    async def get_result_by_id(
        self,
        result_id: str,
        *,
        include_html: bool = True,
    ) -> dict[str, Any]:
        """
        Retrieve full details of a specific scraping result by its ID.

        Args:
            result_id: Unique identifier of the result.  Result IDs are returned
                       by scraper execution methods and by :meth:`get_all_results`.
            include_html: Include stored HTML in the response (default ``True``).

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
        self._validate_token()
        url = f"{_API_BASE_URL}/results/{result_id}?{urlencode({'includeHtml': str(include_html).lower()})}"
        return await self._get(url, headers=self._auth_headers(), timeout=600.0)

    async def get_subscription_account(self) -> dict[str, Any]:
        """Retrieve subscription, token usage, and account information."""
        self._validate_token()
        url = f"{_API_BASE_URL}/subscription-accounts"
        return await self._get(url, headers=self._auth_headers(), timeout=600.0)

    async def get_analytic_statuses(
        self,
        domain: str,
        start_date: str,
        end_date: str,
        *,
        action: str = "",
        api_token_name: str = "",
    ) -> dict[str, Any]:
        """Retrieve request-outcome analytics for a domain and date range."""
        self._validate_token()
        params = {
            "domain": domain,
            "startDate": start_date,
            "endDate": end_date,
            "action": action,
            "apiTokenName": api_token_name,
        }
        url = f"{_API_BASE_URL}/analytic/statuses?{urlencode(params)}"
        return await self._get(url, headers=self._auth_headers(), timeout=600.0)
