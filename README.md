# MrScraper Python SDK

![MrScraper](./mrscraper.jpeg)

An async Python client for the MrScraper API, with seven services matching the [MrScraper CLI](https://github.com/mrscraper-com/cli).

| Service | Python method | Purpose |
| --- | --- | --- |
| [Status](#status) | `status()` | Account identity, subscription, token quota, and rate limits |
| [HTML](#scrape-html) | `scrape_html(url, ...)` | Raw page HTML |
| [Markdown](#scrape-markdown) | `scrape_markdown(url, ...)` | Page content as Markdown, optionally with HTML |
| [Screenshot](#get-screenshot) | `get_screenshot(url, ...)` | Full-page or top-viewport screenshot, optionally with HTML and Markdown |
| [Brand](#scrape-brand) | `scrape_brand(url)` | Website brand data as JSON |
| [JSON extraction](#scrape-json) | `scrape_json(url, prompt=..., ...)` | Structured data extracted according to a prompt |
| [Web search](#web-search) | `web_search(query, ...)` | Ranked search results with titles, URLs, and descriptions |

## Contents

- [Installation and authentication](#installation-and-authentication)
- [Quickstart](#quickstart)
- [Payloads and parameter names](#payloads-and-parameter-names)
- [Shared page parameters](#shared-page-parameters)
- [Service examples](#service-examples)
- [Response format](#response-format)
- [Error handling](#error-handling)
- [Reusing an HTTP client](#reusing-an-http-client)
- [HTTP contract and request payloads](#http-contract-and-request-payloads)
- [Manual testing](#manual-testing)
- [Migration](#migration)
- [Development and publishing](#development-and-publishing)

## Installation and authentication

Requires Python 3.9+. Obtain a MrScraper API token from [the app](https://app.mrscraper.com).

```bash
python3 -m pip install --upgrade mrscraper-sdk
export MRSCRAPER_API_TOKEN='YOUR_MRSCRAPER_TOKEN'
```

Create the client with `MrScraper()` to use the environment variable, or pass `MrScraper(token="YOUR_MRSCRAPER_TOKEN")` explicitly. The client looks for credentials in this order: a nonempty `token` argument, `MRSCRAPER_API_TOKEN`, then `MRSCRAPER_API_KEY`.

| Client argument | Type | Default | Meaning |
| --- | --- | --- | --- |
| `token` | `str` or `None` | `None` | MrScraper API token. When omitted, use the environment variables above. |
| `http_client` | `httpx.AsyncClient` or `None` | `None` | Optional HTTP client to reuse across calls. You manage its lifetime; see [Reusing an HTTP client](#reusing-an-http-client). |

## Quickstart

Save this as `example.py`, then run `python3 example.py` after exporting your token:

```python
import asyncio

from mrscraper import MrScraper


async def main():
    client = MrScraper()
    result = await client.scrape_html("https://example.com")
    print(result["status_code"])
    print(result["data"])


if __name__ == "__main__":
    asyncio.run(main())
```

All seven methods are async and must be awaited. In a notebook with an active event loop, call `await main()` instead of `asyncio.run(main())`. Examples make live API calls and use your account quota.

## Payloads and parameter names

The SDK takes Python arguments. You can collect them in a dictionary named `payload` and unpack it with `**payload`:

```python
payload = {
    "url": "https://example.com",
    "browser_rendering": True,
    "timeout": 120,
}

# Inside an async function, with an initialized client:
# result = await client.scrape_html(**payload)
```

This is equivalent to `await client.scrape_html(url="https://example.com", browser_rendering=True, timeout=120)`. The dictionary is a convenient way to organize arguments; the methods do not accept a `payload=` argument. The service examples below show complete scripts using this pattern.

Use **Python parameter names** in SDK calls and in the manual runner's `--args`. The SDK converts them to the **HTTP parameter names** shown below. For example, use `browser_rendering`, not `browserRendering`, and `num_results`, not `numResults`.

Python dictionaries use `True`, `False`, and `None`. JSON, including `--args`, uses `true`, `false`, and `null`. Optional page controls set to `None` are omitted from the HTTP request. Explicit `False` and `0` values are preserved.

## Shared page parameters

### Page controls

These parameters apply to `scrape_html`, `scrape_markdown`, `get_screenshot`, and `scrape_json`.

| Python parameter | HTTP parameter | Type | Default | Meaning and accepted values |
| --- | --- | --- | --- | --- |
| `url` | `url` | `str` | Required | The page to process. Must be an absolute `http://` or `https://` URL, such as `https://example.com`. |
| `timeout` | `timeout` | `int` | `300` | Page processing deadline in seconds, from `1` to `300`. The SDK uses an HTTP timeout of this value plus 30 seconds. |
| `geo_code` | `geoCode` | `str` | `"us"` | Country code supplied for page geolocation. Must contain two ASCII letters; for example, `"us"` or `"id"`. Sent in lowercase. |
| `proxy_country` | `proxyCountry` | `str` | `"us"` | Country of the proxy server used for the request. Must contain two ASCII letters and is sent in lowercase. |
| `super` | `super` | `bool` | `False` | Request real-device routing when `True`. |
| `wait_until` | `waitUntil` | `str` | `"domcontentloaded"` | Browser loading condition: `"domcontentloaded"`, `"load"`, `"networkidle0"`, or `"networkidle2"`. See below. |
| `proxy` | `proxy` | `str` or `None` | `None` | Custom proxy URL. When provided, it must be a nonempty string. `None` omits the parameter. |
| `max_retries` | `maxRetries` | `int` or `None` | `None` | Retry limit requested from the API. Accepted range: `0` to `2**53 - 1`. `None` omits an explicit retry limit; the SDK does not run its own retry loop. |
| `save_result` | `saveResult` | `bool` | `False` | Save the result in the MrScraper dashboard when `True`. |

`wait_until="domcontentloaded"` requests the DOM-ready condition; `"load"` requests the page load event. `"networkidle0"` and `"networkidle2"` request the API's browser network-idle conditions. Use `browser_rendering=True` when you need browser execution, and `wait_for_selector` when a particular element must be available.

### Rendering, loading, and cookies

| Python parameter | HTTP parameter | Type | Default | Meaning |
| --- | --- | --- | --- | --- |
| `browser_rendering` | `browserRendering` | `bool` | `False` | Enable browser rendering, including JavaScript execution. Available on HTML, Markdown, and JSON extraction. Screenshots always enable rendering and do not take this argument. |
| `block_resources` | `blockResources` | `bool` | `False` | Block images, fonts, and stylesheets. Available on HTML, Markdown, and screenshots. Blocking these resources can change a screenshot's appearance. |
| `wait_for_selector` | `waitForSelector` | `str` or `None` | `None` | Wait for a CSS selector such as `"body"` or `".listing-card"`. A provided selector must be a nonempty string. Available on HTML, Markdown, and screenshots. |
| `return_cookie` | `returnCookie` | `bool` | `False` | Request session cookies in the API response. Available on HTML, Markdown, and screenshots. The SDK preserves the API's response structure. |

| Parameter group | HTML | Markdown | Screenshot | JSON extraction |
| --- | --- | --- | --- | --- |
| Page controls above | Yes | Yes | Yes | Yes |
| `browser_rendering` argument | Yes | Yes | Always enabled internally | Yes |
| `block_resources`, `wait_for_selector`, `return_cookie` | Yes | Yes | Yes | Unavailable |

Status, brand, and web search use their own parameter sets. Their accepted arguments and fixed transport deadlines are described in their service sections.

## Service examples

Each example below is a standalone Python script. They use `https://example.com`; replace the URL or search query for your use case. Fields not included in a payload use the defaults documented above.

### Status

Return the raw account API response. This method takes no service parameters
and uses the same fixed 600-second HTTP deadline as the CLI. Authentication
comes from the client.

```python
import asyncio
import json

from mrscraper import MrScraper


async def main():
    result = await MrScraper().status()
    print(json.dumps(result["data"], indent=2))


if __name__ == "__main__":
    asyncio.run(main())
```

`result["data"]` is the complete API response body with its original fields,
nesting, and values. The SDK does not unwrap it, redact account fields, or
calculate remaining tokens or percentages. Sensitive response headers are
removed. If the API wraps account details in `data`, access them through
`result["data"]["data"]`.

### Scrape HTML

Retrieve the page's HTML. This example lists every supported argument and enables browser rendering to execute JavaScript before returning the page.

```python
import asyncio
from pathlib import Path

from mrscraper import MrScraper


async def main():
    client = MrScraper()
    payload = {
        "url": "https://example.com",
        "timeout": 300,
        "geo_code": "us",
        "proxy_country": "us",
        "super": False,
        "wait_until": "domcontentloaded",
        "proxy": None,
        "max_retries": None,
        "save_result": False,
        "block_resources": False,
        "wait_for_selector": "body",
        "return_cookie": False,
        "browser_rendering": True,
    }
    result = await client.scrape_html(**payload)
    html = result["data"]
    if isinstance(html, str):
        Path("example.html").write_text(html, encoding="utf-8")
    else:
        print(html)  # Inspect the API's structure when extra response data is returned.


if __name__ == "__main__":
    asyncio.run(main())
```

The SDK sets the HTTP output flags `html=true`, `markdown=false`, and `screenshot=false`. These flags are selected by the method and are not arguments to `scrape_html`. A normal HTML response is available as a string at `result["data"]`.

### Scrape Markdown

Retrieve page content as Markdown. In addition to the shared page and loading controls, this method accepts:

| Python / HTTP parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `html` | `bool` | `False` | Include HTML alongside Markdown. Setting this to `True` forces browser rendering, even if `browser_rendering=False`. |

```python
import asyncio
import json

from mrscraper import MrScraper


async def main():
    client = MrScraper()
    payload = {
        "url": "https://example.com",
        "html": True,
        "wait_for_selector": "body",
        "timeout": 120,
    }
    result = await client.scrape_markdown(**payload)
    print(json.dumps(result["data"], indent=2))


if __name__ == "__main__":
    asyncio.run(main())
```

The SDK sets `markdown=true` and `screenshot=false`. With `html=False`, a normal Markdown response is a string. With `html=True`, inspect `result["data"]` for the API's combined HTML and Markdown object; the SDK does not flatten it.

### Get screenshot

Capture a screenshot. Browser rendering is always enabled. Shared page and loading controls are supported, but there is no `browser_rendering` argument.

| Python / HTTP parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `screenshot` | `str` | `"full"` | `"full"` captures the full page; `"top"` captures the top viewport. This parameter is a string for this method. |
| `html` | `bool` | `True` | Include HTML in the response. |
| `markdown` | `bool` | `False` | Include Markdown in the response. |

```python
import asyncio
import base64
from pathlib import Path

from mrscraper import MrScraper


async def main():
    client = MrScraper()
    payload = {
        "url": "https://example.com",
        "screenshot": "full",
        "html": True,
        "markdown": True,
        "block_resources": False,
        "wait_for_selector": "body",
        "timeout": 120,
    }
    result = await client.get_screenshot(**payload)
    data = result["data"]
    if isinstance(data, bytes):
        image_bytes = data
    else:
        encoded = data["screenshot"] if isinstance(data, dict) else data
        # Accept plain base64 or a data URL such as data:image/png;base64,...
        image_bytes = base64.b64decode(encoded.split(",", 1)[-1])
    Path("example-screenshot.png").write_bytes(image_bytes)


if __name__ == "__main__":
    asyncio.run(main())
```

For a combined JSON response, the base64 image is in `result["data"]["screenshot"]`. The example also handles a direct base64 string or a binary image response according to the API's content type.

### Scrape brand

Extract website brand data as JSON. This method only accepts `url`, which must be an absolute HTTP or HTTPS URL. It uses a fixed 120-second HTTP timeout.

```python
import asyncio
import json
from pathlib import Path

from mrscraper import MrScraper


async def main():
    client = MrScraper()
    payload = {"url": "https://example.com"}
    result = await client.scrape_brand(**payload)
    brand_response = result["data"]
    Path("example-brand.json").write_text(
        json.dumps(brand_response, indent=2), encoding="utf-8"
    )
    print(brand_response)


if __name__ == "__main__":
    asyncio.run(main())
```

The SDK adds these HTTP fields automatically:

| HTTP parameter | Fixed value | Meaning |
| --- | --- | --- |
| `action` | `"brand-scraping"` | Select brand extraction. |
| `bundle` | `"none"` | Request the JSON result without downloading a brand bundle. |

Do not pass `action`, `bundle`, or page controls to `scrape_brand`. The SDK returns the API's JSON structure unchanged inside `result["data"]`; inspect that object for the returned brand fields.

### Scrape JSON

Extract structured data according to a prompt. All shared page controls and `browser_rendering` are supported. `block_resources`, `wait_for_selector`, and `return_cookie` are not accepted by this method.

| Python / HTTP parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `prompt` | `str` | `"Extract all data as complete as possible."` | Instructions describing the data to extract. Must contain non-whitespace text. Include field names and missing-value instructions for a more specific result. |
| `html` | `bool` | `False` | Request HTML alongside the extraction. |
| `screenshot` | `bool` | `False` | Request a screenshot alongside the extraction. This method takes `True` or `False`, rather than `"full"` or `"top"`. |

```python
import asyncio
import json
from pathlib import Path

from mrscraper import MrScraper


async def main():
    client = MrScraper()
    payload = {
        "url": "https://example.com",
        "prompt": (
            "Extract property listings visible on this page. "
            "For each listing, return title, price, location, and URL. "
            "Use null for missing fields and return the listings in a listings array."
        ),
        "browser_rendering": True,
        "timeout": 180,
        "html": False,
        "screenshot": False,
    }
    result = await client.scrape_json(**payload)
    Path("example-properties.json").write_text(
        json.dumps(result["data"], indent=2), encoding="utf-8"
    )
    print(result["data"])


if __name__ == "__main__":
    asyncio.run(main())
```

The SDK sets `agent="general"` internally. It preserves the API's extraction response, including any `success`, `data`, or metadata fields, inside `result["data"]`.

To describe an output schema, append `Json Schema:` and a JSON schema to your prompt. For example, this builds a prompt for extracting the page title:

```python
import json

schema = {
    "type": "object",
    "properties": {"title": {"type": "string"}},
    "required": ["title"],
}
prompt = "Extract the page title.\nJson Schema:\n" + json.dumps(schema)
```

Use that string as the `prompt` value in the previous payload. The schema is part of the extraction instructions; the SDK does not validate the response against it. The SDK automatically switches from GET to POST when the complete encoded request URL exceeds 8,000 characters; see [HTTP contract and request payloads](#http-contract-and-request-payloads).

### Web search

Search the web using a query. To focus the search on example.com, the example uses `site:example.com properties`. This service takes a query rather than a target `url`.

| Python parameter | HTTP parameter | Type | Default | Meaning and accepted values |
| --- | --- | --- | --- | --- |
| `query` | `query` | `str` | Required | Search text. Leading and trailing whitespace is removed; the remaining query must contain 1–1,000 characters. |
| `country` | `country` | `str` | `"us"` | Search country. Must contain two ASCII letters, such as `"us"` or `"id"`, and is sent in lowercase. |
| `num_results` | `numResults` | `int` | `10` | Requested number of search results, from `10` to `100`. |

```python
import asyncio

from mrscraper import MrScraper


async def main():
    client = MrScraper()
    payload = {
        "query": "site:example.com properties",
        "country": "us",
        "num_results": 10,
    }
    result = await client.web_search(**payload)
    body = result["data"]
    if body.get("success") is False:
        raise RuntimeError(body.get("message", "Search failed"))
    for item in body["data"]:
        print(item["rank"], item["title"], item["url"])


if __name__ == "__main__":
    asyncio.run(main())
```

The SDK adds `action="websearch"`. A search JSON response contains `success`, `message`, and a `data` array. Each result has `rank`, `title`, `url`, `description`, and `source`. Because the SDK also uses a `data` wrapper, the result array is accessed as `result["data"]["data"]`.

## Response format

Every service returns a dictionary with the same outer fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `status_code` | `int` | Successful HTTP response status. HTTP error statuses raise exceptions instead. |
| `data` | Depends on content type | Parsed response body, preserving the API structure and values for all seven services. |
| `headers` | `dict` | Response headers. Status removes sensitive headers. |

For example, an HTML response is wrapped like this:

```json
{
  "status_code": 200,
  "data": "<html><body>Page content</body></html>",
  "headers": {
    "content-type": "text/html"
  }
}
```

JSON bodies become Python values; HTML, Markdown, and other text bodies remain strings; binary bodies remain `bytes`. Combined outputs retain the upstream JSON structure. Requesting extra outputs or cookies can change the inner response shape, so inspect `result["data"]` before selecting nested fields.

An HTTP 200 response can still contain an API-level failure such as `{"success": false, "message": "..."}`. The SDK preserves that body and does not raise an exception based on its `success` field. Check it when the service returns such a field.

## Error handling

| Exception | Meaning |
| --- | --- |
| `AuthenticationError` | Missing/blank API token or an HTTP 401 response. |
| `APIError` | Other HTTP error statuses. The `status_code` attribute contains the HTTP status when available. |
| `NetworkError` | HTTP transport failure, such as a connection error or timeout. |
| `ValueError` | Invalid parameter value, such as an unsupported URL, timeout, country code, or screenshot mode. |
| `TypeError` | Unsupported method argument, such as passing `return_cookie` to `scrape_json`. |

The three SDK exceptions inherit from `MrScraperError`. Parameter validation errors are standard Python exceptions.

```python
import asyncio

from mrscraper import APIError, AuthenticationError, MrScraper, NetworkError


async def main():
    try:
        result = await MrScraper().scrape_html("https://example.com", timeout=120)
        data = result["data"]
        if isinstance(data, dict) and data.get("success") is False:
            print("API reported failure:", data.get("message"))
            return
        print(data)
    except AuthenticationError as exc:
        print("Check your MrScraper API token:", exc)
    except APIError as exc:
        print(f"API error (HTTP {exc.status_code}): {exc}")
    except NetworkError as exc:
        print("Request failed:", exc)
    except (ValueError, TypeError) as exc:
        print("Check the method arguments:", exc)


if __name__ == "__main__":
    asyncio.run(main())
```

## Reusing an HTTP client

By default, the SDK creates and closes an `httpx.AsyncClient` for each request. For multiple calls, pass a shared client and close it yourself, for example with an async context manager:

```python
import asyncio

import httpx

from mrscraper import MrScraper


async def main():
    async with httpx.AsyncClient() as http_client:
        client = MrScraper(http_client=http_client)
        status = await client.status()
        markdown = await client.scrape_markdown("https://example.com")
        print(status["data"])
        print(markdown["data"])


if __name__ == "__main__":
    asyncio.run(main())
```

The SDK still sets each request's timeout according to the selected service.

## HTTP contract and request payloads

### Endpoints and authentication

These seven services use two API hosts. The Python SDK sends both `Authorization: Bearer YOUR_MRSCRAPER_TOKEN` and `x-api-token: YOUR_MRSCRAPER_TOKEN` headers, along with `Content-Type: application/json` and `accept: application/json`. Credentials are not placed in the query string.

| Service | HTTP method and URL | Service-specific HTTP fields |
| --- | --- | --- |
| Status | `GET https://api.app.mrscraper.com/api/v1/subscription-accounts` | No query parameters or body. |
| HTML | `GET https://api.mrscraper.com` | `html=true`, `markdown=false`, `screenshot=false` |
| Markdown | `GET https://api.mrscraper.com` | `markdown=true`, `screenshot=false`, `html` from the caller |
| Screenshot | `GET https://api.mrscraper.com` | `browserRendering=true`, `screenshot=full` or `top`, `html` and `markdown` from the caller |
| Brand | `GET https://api.mrscraper.com` | `action=brand-scraping`, `url`, `bundle=none` |
| JSON extraction | `GET https://api.mrscraper.com`, or POST for long encoded URLs | `agent=general`, `url`, `prompt`, `html`, `screenshot` |
| Web search | `GET https://api.mrscraper.com` | `action=websearch`, `query`, `country`, `numResults` |

### GET query payloads

The following JSON objects describe query parameters for readability. They are not JSON request bodies: the SDK URL-encodes these fields into the GET URL and serializes booleans as lowercase `true` or `false`.

For `await client.scrape_html("https://example.com")`, the default HTTP query payload is:

```json
{
  "url": "https://example.com",
  "super": false,
  "waitUntil": "domcontentloaded",
  "timeout": 300,
  "geoCode": "us",
  "proxyCountry": "us",
  "saveResult": false,
  "blockResources": false,
  "returnCookie": false,
  "browserRendering": false,
  "html": true,
  "markdown": false,
  "screenshot": false
}
```

The meanings and Python names of the page controls are listed in [Shared page parameters](#shared-page-parameters). The output flags `html`, `markdown`, and `screenshot` select which page outputs the service returns. `proxy`, `maxRetries`, and `waitForSelector` are absent here because their Python defaults are `None`.

For `await client.scrape_brand("https://example.com")`, the entire query payload is:

```json
{
  "action": "brand-scraping",
  "url": "https://example.com",
  "bundle": "none"
}
```

For `await client.web_search("site:example.com properties", num_results=20)`, the entire query payload is:

```json
{
  "action": "websearch",
  "query": "site:example.com properties",
  "country": "us",
  "numResults": 20
}
```

`action` selects the API service, `query` is the search text, `country` selects the search country, and `numResults` requests the result count. The fixed 120-second HTTP timeout is not included in this payload.

For a direct HTTP request equivalent to the basic HTML output selection:

```bash
curl --get 'https://api.mrscraper.com' \
  --header "Authorization: Bearer $MRSCRAPER_API_TOKEN" \
  --header "x-api-token: $MRSCRAPER_API_TOKEN" \
  --data-urlencode 'url=https://example.com' \
  --data-urlencode 'html=true' \
  --data-urlencode 'markdown=false' \
  --data-urlencode 'screenshot=false'
```

This curl command shows the output selection; the full SDK defaults are listed in the query payload above. See the [REST API reference](docs/api-reference.md) for an additional HTTP-oriented reference.

### JSON extraction GET-to-POST fallback

`scrape_json` normally sends `url`, `prompt`, `agent=general`, and its page/output controls as GET query parameters. When the complete encoded URL exceeds 8,000 characters, the SDK switches to POST automatically. Only these three fields move into the JSON request body:

```json
{
  "url": "https://example.com",
  "prompt": "Extract property listings including title, price, location, and URL.",
  "agent": "general"
}
```

`url` identifies the page, `prompt` contains extraction instructions, and `agent` selects the general extraction agent. Other options, such as `timeout`, `browserRendering`, `html`, and `screenshot`, stay in the query string. There is no SDK argument to select the HTTP method manually.

### Timeout summary

| Service | Default | How it is applied |
| --- | --- | --- |
| Status | 600 seconds | Fixed local HTTP timeout; no service arguments. |
| HTML, Markdown, screenshot, JSON extraction | 300 seconds | Page timeout sent to the API; local HTTP timeout is `timeout + 30` seconds. |
| Brand | 120 seconds | Fixed local HTTP timeout. |
| Web search | 120 seconds | Fixed local HTTP timeout; no `timeout` argument. |

## Manual testing

The repository includes `file.py` to call each service and save the result. It imports this checkout's `src/mrscraper` code, so it tests the local SDK. These commands make live requests and consume quota.

```bash
python3 -m pip install -e .
export MRSCRAPER_API_TOKEN='YOUR_MRSCRAPER_TOKEN'

# Run all seven services in order, using the same URL for the page services.
python3 file.py all --url https://example.com --query 'site:example.com properties'

# Or run each service separately.
python3 file.py status
python3 file.py scrape-html --url https://example.com --args '{"browser_rendering":true}'
python3 file.py scrape-markdown --url https://example.com --args '{"html":true}'
python3 file.py get-screenshot --url https://example.com --args '{"screenshot":"full","html":true,"markdown":true}'
python3 file.py scrape-brand --url https://example.com
python3 file.py scrape-json --url https://example.com --args '{"prompt":"Extract property listings including title, price, location, and URL.","browser_rendering":true}'
python3 file.py web-search --query 'site:example.com properties' --args '{"country":"us","num_results":10}'
```

| Runner argument | Default | Meaning |
| --- | --- | --- |
| Positional service name | `all` | One of the seven hyphenated service names above, or `all` to run them sequentially. Underscores are also accepted. |
| `--url` | `https://example.com` | Target URL for HTML, Markdown, screenshot, brand, and JSON extraction. |
| `--query` | `python web scraping` | Search query used by `web-search`. |
| `--args` | `{}` | JSON object of extra method arguments using Python names. Use `--url` and `--query` for their respective values. Nonempty `--args` requires selecting a single service. |
| `--save-dir` | `manual_results` | Parent directory for saved response files. |

Each run creates a timestamped directory with service response JSON files and `summary.json`, and prints a PASS/FAIL summary. A PNG is also saved when the response contains a top-level base64 `screenshot` field inside `result["data"]`. `test_pypi.py` is an alias for this local checkout runner.

## Migration

Replace `client.account()` with `client.status()`. Status now preserves the
raw API response body. Status and web search use fixed HTTP deadlines of
600 and 120 seconds respectively; remove their old `timeout` arguments.

Version 0.10.0 replaces the combined `scraper_api` method with separate services:

| Previous usage | Current usage |
| --- | --- |
| `client.account()` | `client.status()` (raw API body) |
| `client.scraper_api(url)` for HTML | `client.scrape_html(url)` |
| `client.scraper_api(url, html=False, markdown=True)` | `client.scrape_markdown(url)` |
| `client.scraper_api(url, screenshot=True)` | `client.get_screenshot(url)` |
| `full_page=True` / `full_page=False` for screenshots | `screenshot="full"` / `screenshot="top"` |

For combined outputs, use `scrape_markdown(url, html=True)` or `get_screenshot(url, html=True, markdown=True)`. Public `scrape_brand` and `scrape_json` methods are also available.

Page defaults now match the CLI: a 300-second timeout, US geolocation and proxy country, rendering off unless required by the selected service, and no explicit retry limit. Search takes `query`, `country`, and `num_results`; previous URL/locale/raw/format search options are removed. Legacy scraper job, sitemap, rerun, result, and bundle-download methods are outside this seven-service API. LangChain tool names follow `mrscraper_<service>`.

## Development and publishing

From the repository root, install development tools and run the offline suite:

```bash
python3 -m pip install -e . pytest pytest-asyncio respx build twine
python3 -m pytest -m "not integration" -q
```

To opt into live integration tests, set a MrScraper token and run:

```bash
MRSCRAPER_RUN_LIVE=1 python3 -m pytest -m integration -q
```

Version 0.10.0 is configured in `pyproject.toml` and `src/mrscraper/__init__.py`. Build and validate that release:

```bash
python3 -m build --outdir dist/release-0.10.0
python3 -m twine check dist/release-0.10.0/*
```

Publish the wheel and source distribution with:

```bash
python3 -m twine upload --username __token__ \
  dist/release-0.10.0/mrscraper_sdk-0.10.0-py3-none-any.whl \
  dist/release-0.10.0/mrscraper_sdk-0.10.0.tar.gz
```

Use your **PyPI API token** when prompted for the upload credential. The MrScraper API token is for calling services; the PyPI token is for publishing this package. For a subsequent release, update both version fields and the artifact paths. Publish this Python SDK before LangChain 0.6.0, which depends on it.

## License

MIT © MrScraper
