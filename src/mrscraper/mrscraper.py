"""Async client for the MrScraper API."""

from __future__ import annotations

import os
import re
from typing import Any, Literal, Union
from urllib.parse import urlencode, urlparse

import httpx

from .exceptions import APIError, AuthenticationError, NetworkError

_FETCH_BASE_URL = "https://api.mrscraper.com"
_ACCOUNT_URL = "https://api.app.mrscraper.com/api/v1/subscription-accounts"

DEFAULT_JSON_PROMPT = "Extract all data as complete as possible."
#: Scrape HTML screenshot: False for none, "full", "top", or "WIDTHxHEIGHT[-ZOOM]".
ScreenshotCapture = Union[Literal[False], str]

_DEFAULT_TIMEOUT = 300
_MAX_TIMEOUT = 330
_MAX_SELECTOR_LENGTH = 500
# Seven days, the oldest cached result the Scraper API serves.
_MAX_CACHE_AGE_MS = 604_800_000
# The Scraper API refuses request URLs over about 8 KB with 414.
_MAX_GET_URL_LENGTH = 8000
_TRANSPORT_GRACE_SECONDS = 30
_SEARCH_TIMEOUT = 120
_SCREENSHOT_VIEWPORT = re.compile(r"([0-9]{3,4})x([0-9]{3,4})(?:-([0-9]{2,3}))?")


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

    @classmethod
    def _optional_integer(cls, name: str, value: int | None, minimum: int) -> int | None:
        return None if value is None else cls._integer(name, value, minimum)

    @staticmethod
    def _boolean(name: str, value: bool) -> bool:
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be a boolean")
        return value

    @classmethod
    def _optional_boolean(cls, name: str, value: bool | None) -> bool | None:
        return None if value is None else cls._boolean(name, value)

    @staticmethod
    def _text(name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")
        return value.strip()

    @classmethod
    def _optional_text(cls, name: str, value: str | None) -> str | None:
        return None if value is None else cls._text(name, value)

    @classmethod
    def _selector(cls, value: str | None) -> str | None:
        selector = cls._optional_text("wait_for_selector", value)
        if selector is not None and len(selector) > _MAX_SELECTOR_LENGTH:
            raise ValueError(f"wait_for_selector must be at most {_MAX_SELECTOR_LENGTH} characters")
        return selector

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
    def _optional_country(cls, name: str, value: str | None) -> str | None:
        return None if value is None else cls._country(name, value)

    @staticmethod
    def _screenshot_capture(value: ScreenshotCapture) -> ScreenshotCapture:
        """Accept False, full, top, or a WIDTHxHEIGHT viewport with an optional -ZOOM."""
        if value is False:
            return value
        if isinstance(value, str):
            if value in ("full", "top"):
                return value
            match = _SCREENSHOT_VIEWPORT.fullmatch(value)
            if match:
                width, height = int(match[1]), int(match[2])
                zoom = 100 if match[3] is None else int(match[3])
                if 100 <= width <= 3840 and 100 <= height <= 3840 and 25 <= zoom <= 300:
                    return value
        raise ValueError(
            "screenshot must be False, full, top, or WIDTHxHEIGHT from 100 to 3840 pixels "
            "with an optional -ZOOM from 25 to 300, such as 1280x800 or 1920x1080-75"
        )

    @classmethod
    def _page_fields(
        cls, values: dict[str, Any], *, loading: bool, action: bool = False
    ) -> dict[str, Any]:
        """Validate the shared page controls in a method's arguments.

        Returns HTTP fields in the documented request order. Optional controls set
        to ``None`` stay off the wire; explicit ``False`` and ``0`` are preserved.
        """
        fields: dict[str, Any] = {}
        if loading:
            fields["browserRendering"] = cls._optional_boolean(
                "browser_rendering", values["browser_rendering"]
            )
        fields["timeout"] = cls._integer("timeout", values["timeout"], 1, _MAX_TIMEOUT)
        if loading:
            fields["warmStart"] = cls._boolean("warm_start", values["warm_start"])
            fields["blockResources"] = cls._boolean("block_resources", values["block_resources"])
        fields["waitForSelector"] = cls._selector(values["wait_for_selector"])
        if action:
            fields["action"] = cls._optional_text("action", values["action"])
        fields["geoCode"] = cls._optional_country("geo_code", values["geo_code"])
        # Results are always saved to the dashboard; saveResult is not an option.
        fields["saveResult"] = True
        fields["maxAge"] = cls._integer("max_age", values["max_age"], 0, _MAX_CACHE_AGE_MS)
        fields["maxRetries"] = cls._optional_integer("max_retries", values["max_retries"], 0)
        return fields

    @staticmethod
    def _endpoint(params: dict[str, Any]) -> str:
        values = {k: str(v).lower() if isinstance(v, bool) else str(v) for k, v in params.items()}
        return f"{_FETCH_BASE_URL}?{urlencode(values)}"

    async def _page_request(self, params: dict[str, Any]) -> dict[str, Any]:
        self._validate_token()
        params = self._compact(params)
        return await self._request(
            "GET", self._endpoint(params), timeout=params["timeout"] + _TRANSPORT_GRACE_SECONDS
        )

    async def scrape_html(
        self,
        url: str,
        *,
        browser_rendering: bool | None = None,
        timeout: int = 300,
        warm_start: bool = False,
        block_resources: bool = False,
        wait_for_selector: str | None = None,
        action: str | None = None,
        geo_code: str | None = None,
        max_age: int = 0,
        max_retries: int | None = None,
        screenshot: ScreenshotCapture = False,
    ) -> dict[str, Any]:
        """Retrieve the raw HTML of a page. Browser rendering is optional.

        Args:
            url: Absolute HTTP or HTTPS URL of the page to process.
            browser_rendering: Whether to load the page in a browser: true always does and false never does. Omit it to load the page without a browser first and switch to a browser automatically if the request is blocked.
            timeout: Maximum seconds to wait for the scrape, from 1 to 330. The HTTP request allows 30 additional seconds.
            warm_start: Whether to open the site's home page first to warm the session before loading the target URL.
            block_resources: Whether to block images, fonts, and stylesheets while loading the page.
            wait_for_selector: CSS selector or text to wait for on the page before returning the result, up to 500 characters.
            action: Scraper action that routes the request or simply flags it, useful for separating analytics per domain.
            geo_code: Two-letter country code to load the page from, sent in lowercase.
            max_age: Return a cached result of the same request when it is newer than the selected age. A cached result costs the same tokens as the original scrape.
            max_retries: Maximum number of retries, as a nonnegative integer. Omit this parameter for no limit.
            screenshot: Screenshot to capture with the HTML: false for none, full for the entire page, top for the first viewport, or a WIDTHxHEIGHT viewport from 100 to 3840 pixels with an optional -ZOOM percent from 25 to 300, such as 1280x800 or 1920x1080-75. Setting a screenshot also sends browserRendering=true.

        Returns:
            A response envelope containing status_code, data, and headers.
        """
        page = self._url(url)
        fields = self._page_fields(locals(), loading=True, action=True)
        capture = self._screenshot_capture(screenshot)
        if capture is not False:
            # A screenshot needs a rendered page, so it always sends browserRendering=true.
            fields["browserRendering"] = True
        params = {"url": page, "html": True, "markdown": False, **fields, "screenshot": capture}
        return await self._page_request(params)

    async def scrape_markdown(
        self,
        url: str,
        *,
        browser_rendering: bool | None = None,
        timeout: int = 300,
        warm_start: bool = False,
        block_resources: bool = False,
        wait_for_selector: str | None = None,
        action: str | None = None,
        geo_code: str | None = None,
        max_age: int = 0,
        max_retries: int | None = None,
    ) -> dict[str, Any]:
        """Retrieve a page as clean Markdown. Browser rendering is optional.

        Args:
            url: Absolute HTTP or HTTPS URL of the page to process.
            browser_rendering: Whether to load the page in a browser: true always does and false never does. Omit it to load the page without a browser first and switch to a browser automatically if the request is blocked.
            timeout: Maximum seconds to wait for the scrape, from 1 to 330. The HTTP request allows 30 additional seconds.
            warm_start: Whether to open the site's home page first to warm the session before loading the target URL.
            block_resources: Whether to block images, fonts, and stylesheets while loading the page.
            wait_for_selector: CSS selector or text to wait for on the page before returning the result, up to 500 characters.
            action: Scraper action that routes the request or simply flags it, useful for separating analytics per domain.
            geo_code: Two-letter country code to load the page from, sent in lowercase.
            max_age: Return a cached result of the same request when it is newer than the selected age. A cached result costs the same tokens as the original scrape.
            max_retries: Maximum number of retries, as a nonnegative integer. Omit this parameter for no limit.

        Returns:
            A response envelope containing status_code, data, and headers.
        """
        params = {
            "url": self._url(url),
            "markdown": True,
            "html": False,
            "screenshot": False,
            **self._page_fields(locals(), loading=True, action=True),
        }
        return await self._page_request(params)

    async def get_screenshot(
        self,
        url: str,
        *,
        timeout: int = 300,
        wait_for_selector: str | None = None,
        geo_code: str | None = None,
        max_age: int = 0,
        max_retries: int | None = None,
    ) -> dict[str, Any]:
        """Capture a base64 PNG screenshot of the full page. Browser rendering is always enabled.

        Args:
            url: Absolute HTTP or HTTPS URL of the page to process.
            timeout: Maximum seconds to wait for the scrape, from 1 to 330. The HTTP request allows 30 additional seconds.
            wait_for_selector: CSS selector or text to wait for on the page before returning the result, up to 500 characters.
            geo_code: Two-letter country code to load the page from, sent in lowercase.
            max_age: Return a cached result of the same request when it is newer than the selected age. A cached result costs the same tokens as the original scrape.
            max_retries: Maximum number of retries, as a nonnegative integer. Omit this parameter for no limit.

        Returns:
            A response envelope containing status_code, data, and headers.
        """
        params = {
            "url": self._url(url),
            "screenshot": "full",
            "html": False,
            "markdown": False,
            "browserRendering": True,
            **self._page_fields(locals(), loading=False),
        }
        return await self._page_request(params)

    async def scrape_json(
        self,
        url: str,
        prompt: str = DEFAULT_JSON_PROMPT,
        *,
        html: bool = True,
        browser_rendering: bool | None = None,
        timeout: int = 300,
        warm_start: bool = False,
        block_resources: bool = False,
        wait_for_selector: str | None = None,
        geo_code: str | None = None,
        max_age: int = 0,
        max_retries: int | None = None,
        screenshot: bool = False,
    ) -> dict[str, Any]:
        """Extract structured JSON from a page using a natural-language prompt. Append Json Schema: and a JSON schema to shape the output.

        Args:
            url: Absolute HTTP or HTTPS URL of the page to process.
            prompt: Instructions describing the data to extract. Append Json Schema: and a JSON schema to shape the output.
            html: Whether to include the page HTML in the response.
            browser_rendering: Whether to load the page in a browser: true always does and false never does. Omit it to load the page without a browser first and switch to a browser automatically if the request is blocked.
            timeout: Maximum seconds to wait for the scrape, from 1 to 330. The HTTP request allows 30 additional seconds.
            warm_start: Whether to open the site's home page first to warm the session before loading the target URL.
            block_resources: Whether to block images, fonts, and stylesheets while loading the page.
            wait_for_selector: CSS selector or text to wait for on the page before returning the result, up to 500 characters.
            geo_code: Two-letter country code to load the page from, sent in lowercase.
            max_age: Return a cached result of the same request when it is newer than the selected age. A cached result costs the same tokens as the original scrape.
            max_retries: Maximum number of retries, as a nonnegative integer. Omit this parameter for no limit.
            screenshot: Whether to include a base64 screenshot in the response.

        Returns:
            A response envelope containing status_code, data, and headers.
        """
        self._validate_token()
        self._text("prompt", prompt)
        params = self._compact(
            {
                "url": self._url(url),
                "prompt": prompt,
                "agent": "general",
                "html": self._boolean("html", html),
                **self._page_fields(locals(), loading=True),
                "screenshot": self._boolean("screenshot", screenshot),
            }
        )
        transport_timeout = params["timeout"] + _TRANSPORT_GRACE_SECONDS
        endpoint = self._endpoint(params)
        if len(endpoint) <= _MAX_GET_URL_LENGTH:
            return await self._request("GET", endpoint, timeout=transport_timeout)
        body = {key: params.pop(key) for key in ("url", "prompt", "agent")}
        return await self._request(
            "POST", self._endpoint(params), payload=body, timeout=transport_timeout
        )

    async def scrape_brand(
        self,
        url: str,
        *,
        timeout: int | None = None,
        warm_start: bool = False,
        geo_code: str | None = None,
    ) -> dict[str, Any]:
        """Extract a website's colors, typography, logos, and social links as JSON.

        Args:
            url: Absolute HTTP or HTTPS URL of the page to process.
            timeout: Maximum seconds to wait for the scrape, from 1 to 330. The HTTP request allows 30 additional seconds.
            warm_start: Whether to open the site's home page first to warm the session before loading the target URL.
            geo_code: Two-letter country code to load the page from, sent in lowercase.

        Returns:
            A response envelope containing status_code, data, and headers.
        """
        self._validate_token()
        params = self._compact(
            {
                "action": "brand-scraping",
                "url": self._url(url),
                "bundle": "none",
                # timeout and geoCode are sent only when set.
                "timeout": None
                if timeout is None
                else self._integer("timeout", timeout, 1, _MAX_TIMEOUT),
                "warmStart": self._boolean("warm_start", warm_start),
                "geoCode": self._optional_country("geo_code", geo_code),
            }
        )
        deadline = (_DEFAULT_TIMEOUT if timeout is None else timeout) + _TRANSPORT_GRACE_SECONDS
        return await self._request("GET", self._endpoint(params), timeout=deadline)

    async def web_search(
        self,
        query: str,
        *,
        country: str | None = None,
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
        params = self._compact(
            {
                "action": "websearch",
                "query": query,
                "country": self._optional_country("country", country),
                "numResults": self._integer("num_results", num_results, 10, 100),
            }
        )
        return await self._request("GET", self._endpoint(params), timeout=_SEARCH_TIMEOUT)
