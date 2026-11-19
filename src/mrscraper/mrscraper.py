"""Async client for the MrScraper API."""

from __future__ import annotations

import os
from typing import Any, Literal
from urllib.parse import urlencode, urlparse

import httpx

from .exceptions import APIError, AuthenticationError, NetworkError

_FETCH_BASE_URL = "https://api.mrscraper.com"
_ACCOUNT_URL = "https://api.app.mrscraper.com/api/v1/subscription-accounts"

WaitUntil = Literal["domcontentloaded", "load", "networkidle0", "networkidle2"]
DEFAULT_JSON_PROMPT = "Extract all data as complete as possible."


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
            result = await client.scrape_html("https://example.com")
            print(result["data"])

        asyncio.run(main())
    """

    def __init__(
        self,
        token: str | None = None,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._token = (
            token
            or os.environ.get("MRSCRAPER_API_TOKEN")
            or os.environ.get("MRSCRAPER_API_KEY", "")
        )
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
        elif (
            not content_type
            or content_type.startswith("text/")
            or content_type
            in {"application/xml", "application/xhtml+xml", "application/javascript"}
        ):
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

    async def status(self) -> dict[str, Any]:
        """Return the raw account status API response without summarizing, redacting body fields, or adding calculated fields.

        Returns:
            A response envelope containing status_code, data, and headers.
        """
        self._validate_token()
        result = await self._request("GET", _ACCOUNT_URL, timeout=600)
        sensitive_headers = {
            "authorization",
            "proxy-authorization",
            "set-cookie",
            "set-cookie2",
            "x-api-token",
        }
        result["headers"] = {
            key: value
            for key, value in result["headers"].items()
            if key.lower() not in sensitive_headers
        }
        return result

    @staticmethod
    def _integer(name: str, value: int, minimum: int, maximum: int = 2**53 - 1) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
            raise ValueError(f"{name} must be an integer from {minimum} to {maximum}")
        return value

    @staticmethod
    def _text(name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")
        return value.strip()

    @staticmethod
    def _url(url: str) -> str:
        try:
            parsed = urlparse(url)
            valid = parsed.scheme.lower() in {"http", "https"} and parsed.hostname
        except (ValueError, TypeError, AttributeError):
            valid = False
        if not valid:
            raise ValueError("url must be an absolute HTTP or HTTPS URL")
        return url

    @staticmethod
    def _country(name: str, value: str) -> str:
        if (
            not isinstance(value, str)
            or len(value) != 2
            or not value.isascii()
            or not value.isalpha()
        ):
            raise ValueError(f"{name} must be a two-letter country code")
        return value.lower()

    @classmethod
    def _page_params(cls, url: str, options: dict[str, Any]) -> dict[str, Any]:
        wait_until = options["wait_until"]
        if wait_until not in {"domcontentloaded", "load", "networkidle0", "networkidle2"}:
            raise ValueError(
                "wait_until must be domcontentloaded, load, networkidle0, or networkidle2"
            )
        params = {
            "url": cls._url(url),
            "super": options["super"],
            "waitUntil": wait_until,
            "timeout": cls._integer("timeout", options["timeout"], 1, 300),
            "geoCode": cls._country("geo_code", options["geo_code"]),
            "proxyCountry": cls._country("proxy_country", options["proxy_country"]),
            "saveResult": options["save_result"],
        }
        for local, wire in (("proxy", "proxy"), ("wait_for_selector", "waitForSelector")):
            if options.get(local) is not None:
                params[wire] = cls._text(local, options[local])
        if options["max_retries"] is not None:
            params["maxRetries"] = cls._integer("max_retries", options["max_retries"], 0)
        for local, wire in (
            ("block_resources", "blockResources"),
            ("return_cookie", "returnCookie"),
        ):
            if local in options:
                params[wire] = options[local]
        for name in (
            "super",
            "save_result",
            "block_resources",
            "return_cookie",
            "browser_rendering",
            "warm_start",
            "html",
            "markdown",
        ):
            if name in options and not isinstance(options[name], bool):
                raise ValueError(f"{name} must be a boolean")
        return params

    @staticmethod
    def _endpoint(params: dict[str, Any]) -> str:
        values = {k: str(v).lower() if isinstance(v, bool) else str(v) for k, v in params.items()}
        return f"{_FETCH_BASE_URL}?{urlencode(values)}"

    async def _page_request(self, params: dict[str, Any]) -> dict[str, Any]:
        self._validate_token()
        return await self._request("GET", self._endpoint(params), timeout=params["timeout"] + 30)

    async def scrape_html(
        self,
        url: str,
        *,
        timeout: int = 300,
        geo_code: str = "us",
        proxy_country: str = "us",
        super: bool = False,
        wait_until: WaitUntil = "domcontentloaded",
        proxy: str | None = None,
        max_retries: int | None = None,
        save_result: bool = False,
        block_resources: bool = False,
        wait_for_selector: str | None = None,
        return_cookie: bool = False,
        browser_rendering: bool = False,
        warm_start: bool = False,
    ) -> dict[str, Any]:
        """Retrieve the raw HTML of a page. Browser rendering is optional.

        Args:
            url: Absolute HTTP or HTTPS URL of the page to process.
            timeout: Page load timeout in seconds, from 1 to 300. The HTTP request allows 30 additional seconds.
            geo_code: Two-letter country code to load the page from, sent in lowercase.
            proxy_country: Two-letter country code of the proxy server, sent in lowercase.
            super: Whether to route the request through real devices.
            wait_until: Navigation completion event to wait for: domcontentloaded, load, networkidle0, or networkidle2.
            proxy: Custom proxy URL used to load the page.
            max_retries: Maximum number of retries, as a nonnegative integer. Omit this parameter for no limit.
            save_result: Whether to save the result to the dashboard Result tab.
            block_resources: Whether to block images, fonts, and stylesheets while loading the page.
            wait_for_selector: Wait for the page to contain the specified CSS selector before returning the result.
            return_cookie: Whether to include browser session cookies in the response.
            browser_rendering: Whether to render the page in a browser before returning the result.
            warm_start: Whether to enable warm start for more reliable scraping, at the cost of additional latency.

        Returns:
            A response envelope containing status_code, data, and headers.
        """
        params = self._page_params(url, locals())
        params.update(
            browserRendering=browser_rendering,
            warmStart=warm_start,
            html=True,
            markdown=False,
            screenshot=False,
        )
        return await self._page_request(params)

    async def scrape_markdown(
        self,
        url: str,
        *,
        timeout: int = 300,
        geo_code: str = "us",
        proxy_country: str = "us",
        super: bool = False,
        wait_until: WaitUntil = "domcontentloaded",
        proxy: str | None = None,
        max_retries: int | None = None,
        save_result: bool = False,
        block_resources: bool = False,
        wait_for_selector: str | None = None,
        return_cookie: bool = False,
        browser_rendering: bool = False,
        warm_start: bool = False,
        html: bool = False,
    ) -> dict[str, Any]:
        """Retrieve a page as Markdown. Including HTML also enables browser rendering and returns both outputs as JSON.

        Args:
            url: Absolute HTTP or HTTPS URL of the page to process.
            timeout: Page load timeout in seconds, from 1 to 300. The HTTP request allows 30 additional seconds.
            geo_code: Two-letter country code to load the page from, sent in lowercase.
            proxy_country: Two-letter country code of the proxy server, sent in lowercase.
            super: Whether to route the request through real devices.
            wait_until: Navigation completion event to wait for: domcontentloaded, load, networkidle0, or networkidle2.
            proxy: Custom proxy URL used to load the page.
            max_retries: Maximum number of retries, as a nonnegative integer. Omit this parameter for no limit.
            save_result: Whether to save the result to the dashboard Result tab.
            block_resources: Whether to block images, fonts, and stylesheets while loading the page.
            wait_for_selector: Wait for the page to contain the specified CSS selector before returning the result.
            return_cookie: Whether to include browser session cookies in the response.
            browser_rendering: Whether to render the page in a browser before returning the result.
            warm_start: Whether to enable warm start for more reliable scraping, at the cost of additional latency.
            html: Whether to include the page HTML in the response.

        Returns:
            A response envelope containing status_code, data, and headers.
        """
        params = self._page_params(url, locals())
        params.update(
            browserRendering=html or browser_rendering,
            warmStart=warm_start,
            html=html,
            markdown=True,
            screenshot=False,
        )
        return await self._page_request(params)

    async def get_screenshot(
        self,
        url: str,
        *,
        timeout: int = 300,
        geo_code: str = "us",
        proxy_country: str = "us",
        super: bool = False,
        wait_until: WaitUntil = "domcontentloaded",
        proxy: str | None = None,
        max_retries: int | None = None,
        save_result: bool = False,
        block_resources: bool = False,
        wait_for_selector: str | None = None,
        return_cookie: bool = False,
        screenshot: Literal["full", "top"] = "full",
        html: bool = True,
        markdown: bool = False,
    ) -> dict[str, Any]:
        """Capture a base64 screenshot of the full page or top viewport. Browser rendering is always enabled.

        Args:
            url: Absolute HTTP or HTTPS URL of the page to process.
            timeout: Page load timeout in seconds, from 1 to 300. The HTTP request allows 30 additional seconds.
            geo_code: Two-letter country code to load the page from, sent in lowercase.
            proxy_country: Two-letter country code of the proxy server, sent in lowercase.
            super: Whether to route the request through real devices.
            wait_until: Navigation completion event to wait for: domcontentloaded, load, networkidle0, or networkidle2.
            proxy: Custom proxy URL used to load the page.
            max_retries: Maximum number of retries, as a nonnegative integer. Omit this parameter for no limit.
            save_result: Whether to save the result to the dashboard Result tab.
            block_resources: Whether to block images, fonts, and stylesheets while loading the page.
            wait_for_selector: Wait for the page to contain the specified CSS selector before returning the result.
            return_cookie: Whether to include browser session cookies in the response.
            screenshot: Screenshot area to capture: full for the entire page or top for the top viewport.
            html: Whether to include the page HTML in the response.
            markdown: Whether to include the page Markdown in the response.

        Returns:
            A response envelope containing status_code, data, and headers.
        """
        if screenshot not in ("full", "top"):
            raise ValueError("screenshot must be full or top")
        params = self._page_params(url, locals())
        params.update(browserRendering=True, screenshot=screenshot, html=html, markdown=markdown)
        return await self._page_request(params)

    async def scrape_json(
        self,
        url: str,
        prompt: str = DEFAULT_JSON_PROMPT,
        *,
        timeout: int = 300,
        geo_code: str = "us",
        proxy_country: str = "us",
        super: bool = False,
        wait_until: WaitUntil = "domcontentloaded",
        proxy: str | None = None,
        max_retries: int | None = None,
        save_result: bool = False,
        browser_rendering: bool = False,
        html: bool = False,
        screenshot: bool = False,
    ) -> dict[str, Any]:
        """Extract structured JSON from a page using a natural-language prompt. Append Json Schema: and a JSON schema to shape the output.

        Args:
            url: Absolute HTTP or HTTPS URL of the page to process.
            timeout: Page load timeout in seconds, from 1 to 300. The HTTP request allows 30 additional seconds.
            geo_code: Two-letter country code to load the page from, sent in lowercase.
            proxy_country: Two-letter country code of the proxy server, sent in lowercase.
            super: Whether to route the request through real devices.
            wait_until: Navigation completion event to wait for: domcontentloaded, load, networkidle0, or networkidle2.
            proxy: Custom proxy URL used to load the page.
            max_retries: Maximum number of retries, as a nonnegative integer. Omit this parameter for no limit.
            save_result: Whether to save the result to the dashboard Result tab.
            prompt: Instructions describing the data to extract. Append Json Schema: and a JSON schema to shape the output.
            browser_rendering: Whether to render the page in a browser before returning the result.
            html: Whether to include the page HTML in the response.
            screenshot: Whether to include a base64 screenshot in the response.

        Returns:
            A response envelope containing status_code, data, and headers.
        """
        self._validate_token()
        self._text("prompt", prompt)
        if not isinstance(screenshot, bool):
            raise ValueError("screenshot must be a boolean")
        params = self._page_params(url, locals())
        params.update(
            browserRendering=browser_rendering,
            html=html,
            screenshot=screenshot,
            agent="general",
            prompt=prompt,
        )
        endpoint = self._endpoint(params)
        if len(endpoint) <= 8000:
            return await self._request("GET", endpoint, timeout=timeout + 30)
        body = {key: params.pop(key) for key in ("url", "prompt", "agent")}
        return await self._request(
            "POST", self._endpoint(params), payload=body, timeout=timeout + 30
        )

    async def scrape_brand(self, url: str) -> dict[str, Any]:
        """Extract a website's colors, typography, logos, and social links as JSON.

        Args:
            url: Absolute HTTP or HTTPS URL of the page to process.

        Returns:
            A response envelope containing status_code, data, and headers.
        """
        self._validate_token()
        return await self._request(
            "GET",
            self._endpoint(
                {
                    "action": "brand-scraping",
                    "url": self._url(url),
                    "bundle": "none",
                }
            ),
            timeout=120,
        )

    async def web_search(
        self,
        query: str,
        *,
        country: str = "us",
        num_results: int = 10,
    ) -> dict[str, Any]:
        """Search the web and return ranked results with titles, URLs, descriptions, and sources.

        Args:
            query: Search query text, trimmed before sending, containing 1 to 1000 characters.
            country: Two-letter country code to search from, sent in lowercase.
            num_results: Number of search results to request, as an integer from 10 to 100. Fewer results may be returned.

        Returns:
            A response envelope containing status_code, data, and headers.
        """
        self._validate_token()
        query = self._text("query", query)
        if len(query) > 1000:
            raise ValueError("query must be 1 to 1000 characters")
        return await self._request(
            "GET",
            self._endpoint(
                {
                    "action": "websearch",
                    "query": query,
                    "country": self._country("country", country),
                    "numResults": self._integer("num_results", num_results, 10, 100),
                }
            ),
            timeout=120,
        )
