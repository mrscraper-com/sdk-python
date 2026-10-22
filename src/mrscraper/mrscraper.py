"""Async client for the MrScraper API."""

from __future__ import annotations

import json
import math
import os
from typing import Any, Literal
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from .exceptions import APIError, AuthenticationError, NetworkError

_FETCH_BASE_URL = "https://api.mrscraper.com"
_SYNC_BASE_URL = "https://sync.scraper.mrscraper.com"
_ACCOUNT_URL = "https://api.app.mrscraper.com/api/v1/subscription-accounts"

_DEFAULT_TIMEOUT = 120

SerpFormat = Literal["json", "html"]
BrandBundle = Literal["clean", "full", "none"]
BrandOutput = Literal["html", "bundle", "screenshot", "screenshot_full"]


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
            result = await client.scraper_html("https://example.com")
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

    async def _request(
        self,
        method: str,
        url: str,
        *,
        payload: dict[str, Any] | None = None,
        timeout: float = 600.0,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        client = self._client()
        owns_client = self._http_client is None
        try:
            try:
                response = await client.request(
                    method,
                    url,
                    headers=headers or self._bearer_auth_headers(),
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

        content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        data: Any
        if content_type == "application/json" or content_type.endswith("+json"):
            data = response.json()
        elif not content_type or content_type.startswith("text/") or content_type in {
            "application/xml", "application/xhtml+xml", "application/javascript"
        }:
            data = response.text
        else:
            data = response.content
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

    async def account(self, *, timeout: float = 30.0) -> dict[str, Any]:
        """Return account identity, subscription, quota, and rate limits.

        Calls ``GET /subscription-accounts`` using the client's token. The
        response has ``status_code``, ``data``, and ``headers`` keys. ``data``
        contains a summary, excluding API tokens and billing identifiers.
        ``timeout`` is the HTTP deadline in seconds and must be positive.
        """
        self._validate_token()
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be greater than 0 seconds")
        result = await self._request("GET", _ACCOUNT_URL, timeout=timeout)
        body = result["data"]
        details = body.get("data", body) if isinstance(body, dict) else body
        if not isinstance(details, dict):
            raise APIError(
                "Account response must contain an object", status_code=result["status_code"]
            )

        def number_or_zero(value: Any) -> float:
            try:
                parsed = float(value)
            except (ValueError, TypeError):
                return 0
            return parsed if math.isfinite(parsed) else 0

        def string_or_none(value: Any) -> str | None:
            return value if isinstance(value, str) else None

        token_limit = number_or_zero(details.get("tokenLimit"))
        token_usage = number_or_zero(details.get("tokenUsage"))
        user = details.get("user")
        if not isinstance(user, dict):
            user = {}
        result["data"] = {
            "subscription_status": string_or_none(details.get("stripeStatus")),
            "enterprise": bool(details.get("isEnterprise")),
            "token_usage": token_usage,
            "token_limit": token_limit,
            "token_remaining": max(0, token_limit - token_usage),
            "usage_percent": round(token_usage / token_limit * 100, 2) if token_limit > 0 else 0,
            "rate_limit": number_or_zero(details.get("rateLimit")),
            "rate_ttl": number_or_zero(details.get("rateTtl")),
            "auto_renew": bool(details.get("isAutoRenew")),
            "ends_at": string_or_none(details.get("endsAt")),
            "user": {
                "name": string_or_none(user.get("name")),
                "email": string_or_none(user.get("email")),
                "verified": bool(user.get("isVerified")),
            },
        }
        sensitive_headers = {
            "authorization", "proxy-authorization", "set-cookie", "set-cookie2", "x-api-token"
        }
        result["headers"] = {
            key: value for key, value in result["headers"].items()
            if key.lower() not in sensitive_headers
        }
        return result

    async def _scraper_api(
        self,
        url: str,
        *,
        html: bool | None = True,
        markdown: bool | None = False,
        timeout: int = _DEFAULT_TIMEOUT,
        geo_code: str = "US",
        proxy_country: str | None = None,
        block_resources: bool | None = False,
        browser_rendering: bool | None = None,
        super: bool = False,
        use_proxy: bool = True,
        proxy: str | None = None,
        wait_for_selector: str | None = None,
        wait_until: str | None = None,
        home_page: bool = False,
        screenshot: bool | Literal["full"] = False,
        bypass_proxy: bool = False,
        cookie_jar: str | None = None,
        headers: dict[str, str] | str | None = None,
        max_retries: int = 3,
        token_cap: int | None = None,
        stream: bool | None = None,
        discard_token_secret: str = "",
        method: Literal["POST", "GET"] = "POST",
        prompt: str | None = None,
        agent: Literal["general", "listing", "map"] | None = None,
        max_pages: int | None = None,
        max_depth: int | None = None,
        limit: int | None = None,
        include_patterns: str | None = None,
        exclude_patterns: str | None = None,
        action: Literal["brand-scraping"] | None = None,
        bundle: BrandBundle | None = None,
    ) -> dict[str, Any]:
        """Build requests for the format-specific public scraping methods.

        Only selected output flags are sent. Screenshot GETs and brand requests
        carry retry controls in the query; other POSTs carry them in JSON.
        """
        self._validate_token()
        if not math.isfinite(timeout) or timeout < 1 or timeout > 300:
            raise ValueError("timeout must be between 1 and 300 seconds")
        if max_retries < 0:
            raise ValueError("max_retries must be greater than or equal to 0")
        if token_cap is not None and token_cap < 0:
            raise ValueError("token_cap must be greater than or equal to 0")
        if not isinstance(screenshot, bool) and screenshot != "full":
            raise ValueError("screenshot must be a boolean or 'full'")
        for name, value, minimum in (
            ("max_pages", max_pages, 1),
            ("max_depth", max_depth, 0),
            ("limit", limit, 1),
        ):
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value < minimum
            ):
                raise ValueError(f"{name} must be an integer greater than or equal to {minimum}")
        if bundle is not None and bundle not in ("clean", "full", "none"):
            raise ValueError("bundle must be 'clean', 'full', or 'none'")
        if not isinstance(super, bool):
            raise ValueError("super must be a boolean")
        effective_browser_rendering = True if screenshot else browser_rendering
        query_retries = method == "GET" or action == "brand-scraping"
        payload = self._compact(
            {
                "url": url,
                "maxRetries": None if query_retries else max_retries,
                "tokenCap": None if query_retries else token_cap,
                "prompt": prompt,
                "agent": agent,
                "maxPages": max_pages,
                "maxDepth": max_depth,
                "limit": limit,
                "includePatterns": include_patterns,
                "excludePatterns": exclude_patterns,
            }
        )
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
                "waitUntil": wait_until,
                "warmStart": True if home_page else None,
                "screenshot": screenshot if screenshot else None,
                "blockResources": True if block_resources else None,
                "bypassProxy": True if bypass_proxy else None,
                "cookieJar": cookie_jar,
                "headers": json.dumps(headers) if isinstance(headers, dict) else headers,
                "stream": stream,
                "url": url if query_retries else None,
                "maxRetries": max_retries if query_retries else None,
                "tokenCap": token_cap if query_retries else None,
                "action": action,
                "bundle": bundle,
            }
        )
        encoded_query = {
            key: str(value).lower() if isinstance(value, bool) else str(value)
            for key, value in query.items()
        }
        endpoint = f"{_FETCH_BASE_URL}?{urlencode(encoded_query)}"
        return await self._request(
            method,
            endpoint,
            payload=None if method == "GET" else payload,
            headers=request_headers,
            timeout=float(timeout + 30),
        )

    async def scraper_html(
        self,
        url: str,
        *,
        timeout: int = _DEFAULT_TIMEOUT,
        geo_code: str = "US",
        proxy_country: str | None = None,
        block_resources: bool | None = False,
        browser_rendering: bool | None = None,
        super: bool = False,
        use_proxy: bool = True,
        proxy: str | None = None,
        wait_for_selector: str | None = None,
        wait_until: str | None = None,
        home_page: bool = False,
        bypass_proxy: bool = False,
        cookie_jar: str | None = None,
        headers: dict[str, str] | str | None = None,
        max_retries: int = 3,
        token_cap: int | None = None,
        stream: bool | None = None,
        discard_token_secret: str = "",
    ) -> dict[str, Any]:
        """Fetch HTML with ``html=true``; omit Markdown and screenshot flags.

        ``home_page`` maps to ``warmStart``. Shared page, proxy, header, and
        retry controls are supported by all scraping methods. The response
        has ``status_code``, ``data``, and ``headers`` keys.
        """
        return await self._scraper_api(
            url,
            html=True,
            markdown=None,
            timeout=timeout,
            geo_code=geo_code,
            proxy_country=proxy_country,
            block_resources=block_resources,
            browser_rendering=browser_rendering,
            super=super,
            use_proxy=use_proxy,
            proxy=proxy,
            wait_for_selector=wait_for_selector,
            wait_until=wait_until,
            home_page=home_page,
            bypass_proxy=bypass_proxy,
            cookie_jar=cookie_jar,
            headers=headers,
            max_retries=max_retries,
            token_cap=token_cap,
            stream=stream,
            discard_token_secret=discard_token_secret,
        )

    async def scraper_markdown(
        self,
        url: str,
        *,
        timeout: int = _DEFAULT_TIMEOUT,
        geo_code: str = "US",
        proxy_country: str | None = None,
        block_resources: bool | None = False,
        browser_rendering: bool | None = None,
        super: bool = False,
        use_proxy: bool = True,
        proxy: str | None = None,
        wait_for_selector: str | None = None,
        wait_until: str | None = None,
        home_page: bool = False,
        bypass_proxy: bool = False,
        cookie_jar: str | None = None,
        headers: dict[str, str] | str | None = None,
        max_retries: int = 3,
        token_cap: int | None = None,
        stream: bool | None = None,
        discard_token_secret: str = "",
    ) -> dict[str, Any]:
        """Fetch Markdown with ``markdown=true``; omit HTML and screenshot flags.

        Returns the usual ``status_code``, ``data``, and ``headers`` wrapper.
        """
        return await self._scraper_api(
            url,
            html=None,
            markdown=True,
            timeout=timeout,
            geo_code=geo_code,
            proxy_country=proxy_country,
            block_resources=block_resources,
            browser_rendering=browser_rendering,
            super=super,
            use_proxy=use_proxy,
            proxy=proxy,
            wait_for_selector=wait_for_selector,
            wait_until=wait_until,
            home_page=home_page,
            bypass_proxy=bypass_proxy,
            cookie_jar=cookie_jar,
            headers=headers,
            max_retries=max_retries,
            token_cap=token_cap,
            stream=stream,
            discard_token_secret=discard_token_secret,
        )

    async def get_screenshot(
        self,
        url: str,
        *,
        full_page: bool = True,
        timeout: int = 300,
        geo_code: str = "US",
        proxy_country: str | None = None,
        block_resources: bool | None = False,
        super: bool = False,
        use_proxy: bool = True,
        proxy: str | None = None,
        wait_for_selector: str | None = None,
        wait_until: str | None = "domcontentloaded",
        home_page: bool = False,
        bypass_proxy: bool = False,
        cookie_jar: str | None = None,
        headers: dict[str, str] | str | None = None,
        max_retries: int = 3,
        token_cap: int | None = None,
        stream: bool | None = None,
        discard_token_secret: str = "",
    ) -> dict[str, Any]:
        """Capture a screenshot using GET with browser rendering enabled.

        ``full_page=True`` sends ``screenshot=full``; ``False`` sends
        ``screenshot=true``. The target URL and retry controls go in the query.
        HTML and Markdown flags are omitted. Image responses are returned as
        bytes in ``data``; JSON responses retain the API's original structure.
        """
        if not isinstance(full_page, bool):
            raise ValueError("full_page must be a boolean")
        return await self._scraper_api(
            url,
            method="GET",
            html=None,
            markdown=None,
            screenshot="full" if full_page else True,
            browser_rendering=True,
            timeout=timeout,
            geo_code=geo_code,
            proxy_country=proxy_country,
            block_resources=block_resources,
            super=super,
            use_proxy=use_proxy,
            proxy=proxy,
            wait_for_selector=wait_for_selector,
            wait_until=wait_until,
            home_page=home_page,
            bypass_proxy=bypass_proxy,
            cookie_jar=cookie_jar,
            headers=headers,
            max_retries=max_retries,
            token_cap=token_cap,
            stream=stream,
            discard_token_secret=discard_token_secret,
        )

    async def scraper_json(
        self,
        url: str,
        prompt: str = "Extract all data as complete as possible.",
        *,
        timeout: int = _DEFAULT_TIMEOUT,
        geo_code: str = "US",
        proxy_country: str | None = None,
        block_resources: bool | None = False,
        browser_rendering: bool | None = None,
        super: bool = False,
        use_proxy: bool = True,
        proxy: str | None = None,
        wait_for_selector: str | None = None,
        wait_until: str | None = None,
        home_page: bool = False,
        bypass_proxy: bool = False,
        cookie_jar: str | None = None,
        headers: dict[str, str] | str | None = None,
        max_retries: int = 3,
        token_cap: int | None = None,
        stream: bool | None = None,
        discard_token_secret: str = "",
    ) -> dict[str, Any]:
        """Extract structured data with ``agent=general`` and ``html=true``.

        ``prompt`` is sent in the JSON body. Markdown and screenshot flags
        are omitted. JSON responses are parsed into Python values in ``data``.
        """
        return await self._scraper_api(
            url,
            html=True,
            markdown=None,
            agent="general",
            prompt=prompt,
            timeout=timeout,
            geo_code=geo_code,
            proxy_country=proxy_country,
            block_resources=block_resources,
            browser_rendering=browser_rendering,
            super=super,
            use_proxy=use_proxy,
            proxy=proxy,
            wait_for_selector=wait_for_selector,
            wait_until=wait_until,
            home_page=home_page,
            bypass_proxy=bypass_proxy,
            cookie_jar=cookie_jar,
            headers=headers,
            max_retries=max_retries,
            token_cap=token_cap,
            stream=stream,
            discard_token_secret=discard_token_secret,
        )

    async def scraper_multiple_page(
        self,
        url: str,
        prompt: str = "Extract all entry data as complete as possible.",
        *,
        max_pages: int = 3,
        timeout: int = _DEFAULT_TIMEOUT,
        geo_code: str = "US",
        proxy_country: str | None = None,
        block_resources: bool | None = False,
        browser_rendering: bool | None = None,
        super: bool = False,
        use_proxy: bool = True,
        proxy: str | None = None,
        wait_for_selector: str | None = None,
        wait_until: str | None = None,
        home_page: bool = False,
        bypass_proxy: bool = False,
        cookie_jar: str | None = None,
        headers: dict[str, str] | str | None = None,
        max_retries: int = 3,
        token_cap: int | None = None,
        stream: bool | None = None,
        discard_token_secret: str = "",
    ) -> dict[str, Any]:
        """Extract entries across pages using ``agent=listing``.

        ``prompt`` and ``maxPages`` are JSON body fields. Output flags are
        omitted. ``max_pages`` must be a positive integer.
        """
        return await self._scraper_api(
            url,
            html=None,
            markdown=None,
            agent="listing",
            prompt=prompt,
            max_pages=max_pages,
            timeout=timeout,
            geo_code=geo_code,
            proxy_country=proxy_country,
            block_resources=block_resources,
            browser_rendering=browser_rendering,
            super=super,
            use_proxy=use_proxy,
            proxy=proxy,
            wait_for_selector=wait_for_selector,
            wait_until=wait_until,
            home_page=home_page,
            bypass_proxy=bypass_proxy,
            cookie_jar=cookie_jar,
            headers=headers,
            max_retries=max_retries,
            token_cap=token_cap,
            stream=stream,
            discard_token_secret=discard_token_secret,
        )

    async def scraper_sitemap(
        self,
        url: str,
        *,
        max_depth: int = 2,
        max_pages: int = 3,
        limit: int = 1000,
        include_patterns: str | None = None,
        exclude_patterns: str | None = None,
        timeout: int = _DEFAULT_TIMEOUT,
        geo_code: str = "US",
        proxy_country: str | None = None,
        block_resources: bool | None = False,
        browser_rendering: bool | None = None,
        super: bool = False,
        use_proxy: bool = True,
        proxy: str | None = None,
        wait_for_selector: str | None = None,
        wait_until: str | None = None,
        home_page: bool = False,
        bypass_proxy: bool = False,
        cookie_jar: str | None = None,
        headers: dict[str, str] | str | None = None,
        max_retries: int = 3,
        token_cap: int | None = None,
        stream: bool | None = None,
        discard_token_secret: str = "",
    ) -> dict[str, Any]:
        """Discover URLs using ``agent=map`` and optional URL patterns.

        ``max_depth``, ``max_pages``, and ``limit`` map to ``maxDepth``,
        ``maxPages``, and ``limit`` in the JSON body. ``include_patterns`` and
        ``exclude_patterns`` map to ``includePatterns`` and ``excludePatterns``.
        Pattern strings are preserved as supplied; unset patterns are omitted.
        No HTML, Markdown, or screenshot flags are sent.
        """
        return await self._scraper_api(
            url,
            html=None,
            markdown=None,
            agent="map",
            max_depth=max_depth,
            max_pages=max_pages,
            limit=limit,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            timeout=timeout,
            geo_code=geo_code,
            proxy_country=proxy_country,
            block_resources=block_resources,
            browser_rendering=browser_rendering,
            super=super,
            use_proxy=use_proxy,
            proxy=proxy,
            wait_for_selector=wait_for_selector,
            wait_until=wait_until,
            home_page=home_page,
            bypass_proxy=bypass_proxy,
            cookie_jar=cookie_jar,
            headers=headers,
            max_retries=max_retries,
            token_cap=token_cap,
            stream=stream,
            discard_token_secret=discard_token_secret,
        )

    async def scrape_brand(
        self,
        url: str,
        *,
        bundle: BrandBundle = "clean",
        timeout: int = _DEFAULT_TIMEOUT,
        geo_code: str = "US",
        proxy_country: str | None = None,
        block_resources: bool | None = False,
        browser_rendering: bool | None = None,
        super: bool = False,
        use_proxy: bool = True,
        proxy: str | None = None,
        wait_for_selector: str | None = None,
        wait_until: str | None = None,
        home_page: bool = False,
        bypass_proxy: bool = False,
        cookie_jar: str | None = None,
        headers: dict[str, str] | str | None = None,
        max_retries: int = 3,
        token_cap: int | None = None,
        stream: bool | None = None,
        discard_token_secret: str = "",
    ) -> dict[str, Any]:
        """Start brand scraping with a ``clean``, ``full``, or ``none`` bundle.

        The query contains ``action=brand-scraping``, ``bundle``, and ``url``;
        the JSON body contains ``url``. Use the returned job ID with
        :meth:`get_brand` to read the job or download an output.
        """
        return await self._scraper_api(
            url,
            html=None,
            markdown=None,
            action="brand-scraping",
            bundle=bundle,
            timeout=timeout,
            geo_code=geo_code,
            proxy_country=proxy_country,
            block_resources=block_resources,
            browser_rendering=browser_rendering,
            super=super,
            use_proxy=use_proxy,
            proxy=proxy,
            wait_for_selector=wait_for_selector,
            wait_until=wait_until,
            home_page=home_page,
            bypass_proxy=bypass_proxy,
            cookie_jar=cookie_jar,
            headers=headers,
            max_retries=max_retries,
            token_cap=token_cap,
            stream=stream,
            discard_token_secret=discard_token_secret,
        )

    async def get_brand(
        self,
        job_id: str,
        *,
        output: BrandOutput | None = None,
        timeout: float = 600.0,
    ) -> dict[str, Any]:
        """Read a brand job or download one of its outputs.

        ``output`` accepts ``html``, ``bundle``, ``screenshot``, or
        ``screenshot_full``. Omit it to read job data. The return value uses
        the usual response wrapper: JSON becomes Python values, HTML becomes
        text, and ZIP/image downloads remain bytes in ``data``.
        """
        self._validate_token()
        if not isinstance(job_id, str) or not job_id.strip():
            raise ValueError("job_id must be a non-empty string")
        if output is not None and output not in ("html", "bundle", "screenshot", "screenshot_full"):
            raise ValueError("output must be 'html', 'bundle', 'screenshot', or 'screenshot_full'")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be greater than 0 seconds")
        query = urlencode(self._compact({"id": job_id, "output": output}))
        return await self._request("GET", f"{_FETCH_BASE_URL}/neo/brand?{query}", timeout=timeout)

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
        return await self._request(
            "POST",
            endpoint,
            payload=payload,
            headers=self._bearer_auth_headers(),
            timeout=timeout,
        )
