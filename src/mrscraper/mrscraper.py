"""Async client for the MrScraper API."""

from __future__ import annotations

import json
import os
from typing import Any, Literal
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from .exceptions import APIError, AuthenticationError, NetworkError

_FETCH_BASE_URL = "https://api.mrscraper.com"
_SYNC_BASE_URL = "https://sync.scraper.mrscraper.com"

_DEFAULT_TIMEOUT = 120

SerpFormat = Literal["json", "html"]


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
        from mrscraper import MrScraper

        async def main():
            client = MrScraper(token="YOUR_TOKEN")
            result = await client.scraper_api("https://example.com")
            print(result["data"])

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
                raise NetworkError(self._safe_http_error(exc)) from exc
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
    def _safe_http_error(exc: httpx.HTTPError) -> str:
        message = str(exc)
        try:
            request = exc.request
        except RuntimeError:
            return message
        if "token" in request.url.params:
            safe_url = request.url.copy_set_param("token", "[REDACTED]")
            return message.replace(str(request.url), str(safe_url))
        return message

    @staticmethod
    def _raise_for_status(exc: httpx.HTTPStatusError) -> None:
        status_code = exc.response.status_code
        if status_code == 401:
            raise AuthenticationError(
                "Unauthorized or invalid token. "
                "Please go to https://app.mrscraper.com to get your token."
            ) from exc
        raise APIError(MrScraper._safe_http_error(exc), status_code=status_code) from exc

    async def scraper_api(
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
        super: bool = False,
        use_proxy: bool = True,
        proxy: str | None = None,
        wait_for_selector: str | None = None,
        home_page: bool = False,
        screenshot: bool = False,
        bypass_proxy: bool = False,
        cookie_jar: str | None = None,
        headers: dict[str, str] | str | None = None,
        max_retries: int = 3,
        token_cap: int | None = None,
        stream: bool | None = None,
        discard_token_secret: str = "",
    ) -> dict[str, Any]:
        """
        Fetch page content via the MrScraper stealth browser.

        The service handles JavaScript rendering, bot detection evasion, and
        optional geolocation proxying for you.

        Page options are sent as query parameters. The JSON body contains the
        target URL and optional retry controls.

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
                               before falling back to browser rendering. Screenshot
                               requests always enable browser rendering.
            super: Use real-device routing independently of browser rendering
                   (default ``False``).
            use_proxy: Whether the service may use a configured proxy.
            proxy: Custom proxy in ``username:password@host:port`` form.
            wait_for_selector: CSS selector to wait for before returning content.
            home_page: Visit the site's root page before the target URL.
                       Sent as ``warmStart=true`` in the query when enabled.
            screenshot: Capture a screenshot when ``True`` (default ``False``).
                        Also enables ``browserRendering`` automatically.
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
            A dict with keys ``status_code``, ``data``, and ``headers``.
            The API response in ``data`` may include HTML, Markdown, a
            screenshot, or a combination, depending on the requested options.

        Raises:
            AuthenticationError: If the API token is invalid.
            APIError: If the API returns a non-2xx error.
            NetworkError: If a connection or timeout error occurs.

        Example::

            result = await client.scraper_api(
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
        if not isinstance(screenshot, bool):
            raise ValueError("screenshot must be a boolean")
        if not isinstance(super, bool):
            raise ValueError("super must be a boolean")
        effective_browser_rendering = True if screenshot else browser_rendering
        payload = self._compact({"url": url, "maxRetries": max_retries, "tokenCap": token_cap})
        request_headers = self._bearer_auth_headers()
        if discard_token_secret:
            request_headers["x-discard-token-secret"] = discard_token_secret
        query = self._compact(
            {
                "token": self._token,
                "timeout": timeout,
                "geoCode": geo_code,
                "proxyCountry": proxy_country,
                "browserRendering": effective_browser_rendering,
                "super": True if super else None,
                "useProxy": False if not use_proxy else None,
                "proxy": proxy,
                "html": html,
                "markdown": markdown,
                "waitForSelector": wait_for_selector,
                "warmStart": True if home_page else None,
                "screenshot": True if screenshot else None,
                "blockResources": True if block_resources else None,
                "bypassProxy": True if bypass_proxy else None,
                "cookieJar": cookie_jar,
                "headers": json.dumps(headers) if isinstance(headers, dict) else headers,
                "stream": stream,
            }
        )
        encoded_query = {
            key: str(value).lower() if isinstance(value, bool) else str(value)
            for key, value in query.items()
        }
        endpoint = f"{_FETCH_BASE_URL}?{urlencode(encoded_query)}"
        return await self._post(
            endpoint,
            payload=payload,
            headers=request_headers,
            timeout=float(timeout + 30),
        )

    async def web_search(
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

            result = await client.web_search(
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
