# MrScraper Python SDK

![MrScraper](./mrscraper.jpeg)

An async Python client for the seven MrScraper services.

## Overview

Seven services share the same descriptions, parameter meanings, and defaults across the CLI, SDKs, and integrations. Names, types, authentication, and code examples follow each surface's conventions. See the [API Reference](https://docs.mrscraper.com/docs/api/overview).

| Service                             | Public name       | Description                                                                                                                      |
| ----------------------------------- | ----------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| [Status](#status)                   | `status`          | Return the raw account status API response without summarizing, redacting body fields, or adding calculated fields.              |
| [Scrape HTML](#scrape-html)         | `scrape_html`     | Retrieve the raw HTML of a page. Browser rendering is optional.                                                                  |
| [Scrape Markdown](#scrape-markdown) | `scrape_markdown` | Retrieve a page as clean Markdown. Browser rendering is optional.                                                                |
| [Get screenshot](#get-screenshot)   | `get_screenshot`  | Capture a base64 PNG screenshot of the full page, the first viewport, or a custom viewport. Browser rendering is always enabled. |
| [Scrape brand](#scrape-brand)       | `scrape_brand`    | Extract a website's colors, typography, logos, and social links as JSON.                                                         |
| [Scrape JSON](#scrape-json)         | `scrape_json`     | Extract structured JSON from a page using a natural-language prompt. Append Json Schema: and a JSON schema to shape the output.  |
| [Web search](#web-search)           | `web_search`      | Search the web and return ranked results with titles, URLs, descriptions, and sources.                                           |

## Installation

Requires Python 3.9 or newer.

```bash
python -m pip install --upgrade mrscraper-sdk
```

## Authentication

Obtain an API key from [the MrScraper app](https://app.mrscraper.com/api-tokens). API key used to authenticate the request.

```bash
export MRSCRAPER_API_TOKEN="YOUR_TOKEN"
```

Use `MrScraper()` to read the environment or `MrScraper(token="YOUR_TOKEN")` for an explicit credential. Precedence is a nonempty `token`, `MRSCRAPER_API_TOKEN`, then `MRSCRAPER_API_KEY`. Authentication belongs to the client, not individual service parameters.

## Quickstart

```python
import asyncio
from mrscraper import MrScraper

async def main():
    client = MrScraper()
    result = await client.scrape_html('https://example.com', browser_rendering=True, warm_start=True, wait_for_selector='body', timeout=120, max_retries=0)
    print(result["data"])

asyncio.run(main())
```

Examples use `example.com` as the sample target. Replace it for your use case. Live scraping and search calls consume account quota.

Response examples show selected keys and types observed in live API responses. Values are placeholders; page content, base64 images, and arrays are abbreviated. Actual responses may contain additional fields.

## Shared parameters

### Page controls

HTML, Markdown, screenshots, and JSON extraction share `url`, `timeout`, `waitForSelector`, `geoCode`, `maxAge`, and `maxRetries` (using the naming style shown below). Defaults are a 300-second timeout (up to 330) and a `maxAge` of 0 milliseconds, which always scrapes fresh; `maxAge` accepts up to 604800000 (7 days). `geoCode` and `maxRetries` are omitted unless set, so the API loads the page from the United States with no retry limit. Results are always saved to the dashboard (`saveResult=true`), and `tokenCap` is never sent. Exact types, defaults, and standard descriptions appear in each service table.

### Loading controls

HTML, Markdown, and JSON extraction also accept `browserRendering`, `warmStart`, and `blockResources`. `browserRendering` is omitted unless set: the API loads the page without a browser first and switches to one if the request is blocked, while `true` always renders and `false` never does. Screenshots always render in a browser: Get screenshot sends `browserRendering=true`, and so does Scrape HTML whenever a screenshot is set.

### Fixed request fields

Each service adds its documented fixed fields automatically, so they are not service parameters: `html=true` and `markdown=false` for HTML (plus `browserRendering=true` when a screenshot is set), `markdown=true`, `html=false`, and `screenshot=false` for Markdown, `browserRendering=true`, `html=false`, and `markdown=false` for screenshots, `action=brand-scraping` and `bundle=none` for brand, `agent=general` for JSON extraction, and `action=websearch` for search. HTML, Markdown, screenshots, and JSON extraction also always send `saveResult=true`.

## Service reference

### Status

#### Description

Return the raw account status API response without summarizing, redacting body fields, or adding calculated fields.

#### Parameters

This service takes no service parameters. Authentication is configured separately.

The HTTP deadline is fixed at 600 seconds. It is not a service parameter.

#### Example

```python
import asyncio
from mrscraper import MrScraper

async def main():
    client = MrScraper()
    result = await client.status()
    print(result["data"])

asyncio.run(main())
```

#### Response

The API body contains message and data. Account details remain nested in data, including subscriptionItem and scraperAllowance. The response envelope therefore exposes account details at data.data. Sensitive response headers are removed.

**Success response**

```json
{
  "status_code": 200,
  "data": {
    "message": "Example response",
    "data": {
      "id": "ACCOUNT_ID",
      "tokenLimit": 100000,
      "tokenUsage": 2500,
      "stripeStatus": "active",
      "user": {
        "name": "Example user",
        "email": "user@example.com",
        "isVerified": true
      },
      "subscriptionItem": {
        "name": "Example plan",
        "tokenLimit": 100000
      },
      "scraperAllowance": {
        "remaining": 97500,
        "plans": [
          {
            "remaining": 97500
          }
        ]
      }
    }
  },
  "headers": {
    "content-type": "application/json; charset=utf-8"
  }
}
```

### Scrape HTML

#### Description

Retrieve the raw HTML of a page. Browser rendering is optional.

#### Parameters

| Parameter           | HTTP field         | Type           | Default          | Description                                                                                                                                                                                                                                                                                           |
| ------------------- | ------------------ | -------------- | ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `url`               | `url`              | str            | Required         | Absolute HTTP or HTTPS URL of the page to process.                                                                                                                                                                                                                                                    |
| `browser_rendering` | `browserRendering` | bool           | `None` (omitted) | Whether to load the page in a browser: true always does and false never does. Omit it to load the page without a browser first and switch to a browser automatically if the request is blocked.                                                                                                       |
| `timeout`           | `timeout`          | int            | `300`            | Maximum seconds to wait for the scrape, from 1 to 330. The HTTP request allows 30 additional seconds.                                                                                                                                                                                                 |
| `warm_start`        | `warmStart`        | bool           | `False`          | Whether to open the site's home page first to warm the session before loading the target URL.                                                                                                                                                                                                         |
| `block_resources`   | `blockResources`   | bool           | `False`          | Whether to block images, fonts, and stylesheets while loading the page.                                                                                                                                                                                                                               |
| `wait_for_selector` | `waitForSelector`  | str            | `None` (omitted) | CSS selector or text to wait for on the page before returning the result, up to 500 characters.                                                                                                                                                                                                       |
| `geo_code`          | `geoCode`          | str            | `None` (omitted) | Two-letter country code to load the page from, sent in lowercase.                                                                                                                                                                                                                                     |
| `max_age`           | `maxAge`           | int            | `0`              | Return a cached result of the same request when it is newer than the selected age. A cached result costs the same tokens as the original scrape.                                                                                                                                                      |
| `max_retries`       | `maxRetries`       | int            | `None` (omitted) | Maximum number of retries, as a nonnegative integer. Omit this parameter for no limit.                                                                                                                                                                                                                |
| `screenshot`        | `screenshot`       | `False` or str | `False`          | Screenshot to capture with the HTML: false for none, full for the entire page, top for the first viewport, or a WIDTHxHEIGHT viewport from 100 to 3840 pixels with an optional -ZOOM percent from 25 to 300, such as 1280x800 or 1920x1080-75. Setting a screenshot also sends browserRendering=true. |

The request uses `html=true`, `markdown=false`, and `saveResult=true`. The screenshot is optional; setting one also sends `browserRendering=true`, because a screenshot needs a rendered page, and the response becomes JSON with `html` and `screenshot`.

#### Example

```python
import asyncio
from mrscraper import MrScraper

async def main():
    client = MrScraper()
    result = await client.scrape_html('https://example.com', browser_rendering=True, warm_start=True, wait_for_selector='body', timeout=120, max_retries=0)
    print(result["data"])

asyncio.run(main())
```

#### Response

The response body is HTML text. With a screenshot, the API returns JSON containing html and a base64 screenshot.

**Default HTML text**

```json
{
  "status_code": 200,
  "data": "<html><body>Example page content...</body></html>",
  "headers": {
    "content-type": "text/html; charset=utf-8"
  }
}
```

**With a screenshot**

```json
{
  "status_code": 200,
  "data": {
    "html": "<html>...</html>",
    "screenshot": "BASE64_IMAGE_DATA"
  },
  "headers": {
    "content-type": "application/json; charset=utf-8"
  }
}
```

### Scrape Markdown

#### Description

Retrieve a page as clean Markdown. Browser rendering is optional.

#### Parameters

| Parameter           | HTTP field         | Type | Default          | Description                                                                                                                                                                                     |
| ------------------- | ------------------ | ---- | ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `url`               | `url`              | str  | Required         | Absolute HTTP or HTTPS URL of the page to process.                                                                                                                                              |
| `browser_rendering` | `browserRendering` | bool | `None` (omitted) | Whether to load the page in a browser: true always does and false never does. Omit it to load the page without a browser first and switch to a browser automatically if the request is blocked. |
| `timeout`           | `timeout`          | int  | `300`            | Maximum seconds to wait for the scrape, from 1 to 330. The HTTP request allows 30 additional seconds.                                                                                           |
| `warm_start`        | `warmStart`        | bool | `False`          | Whether to open the site's home page first to warm the session before loading the target URL.                                                                                                   |
| `block_resources`   | `blockResources`   | bool | `False`          | Whether to block images, fonts, and stylesheets while loading the page.                                                                                                                         |
| `wait_for_selector` | `waitForSelector`  | str  | `None` (omitted) | CSS selector or text to wait for on the page before returning the result, up to 500 characters.                                                                                                 |
| `geo_code`          | `geoCode`          | str  | `None` (omitted) | Two-letter country code to load the page from, sent in lowercase.                                                                                                                               |
| `max_age`           | `maxAge`           | int  | `0`              | Return a cached result of the same request when it is newer than the selected age. A cached result costs the same tokens as the original scrape.                                                |
| `max_retries`       | `maxRetries`       | int  | `None` (omitted) | Maximum number of retries, as a nonnegative integer. Omit this parameter for no limit.                                                                                                          |

The request uses `markdown=true`, `html=false`, `screenshot=false`, and `saveResult=true`.

#### Example

```python
import asyncio
from mrscraper import MrScraper

async def main():
    client = MrScraper()
    result = await client.scrape_markdown('https://example.com', warm_start=True, max_age=86400000)
    print(result["data"])

asyncio.run(main())
```

#### Response

The response body is Markdown text.

**Default Markdown text**

```json
{
  "status_code": 200,
  "data": "# Example page\n\nExample Markdown content...",
  "headers": {
    "content-type": "text/markdown; charset=utf-8"
  }
}
```

### Get screenshot

#### Description

Capture a base64 PNG screenshot of the full page, the first viewport, or a custom viewport. Browser rendering is always enabled.

#### Parameters

| Parameter           | HTTP field        | Type | Default          | Description                                                                                                                                                                                                                    |
| ------------------- | ----------------- | ---- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `url`               | `url`             | str  | Required         | Absolute HTTP or HTTPS URL of the page to process.                                                                                                                                                                             |
| `screenshot`        | `screenshot`      | str  | `"full"`         | Screenshot area to capture: full for the entire scroll height, top for the first viewport, or a WIDTHxHEIGHT viewport from 100 to 3840 pixels with an optional -ZOOM percent from 25 to 300, such as 1280x800 or 1920x1080-75. |
| `timeout`           | `timeout`         | int  | `300`            | Maximum seconds to wait for the scrape, from 1 to 330. The HTTP request allows 30 additional seconds.                                                                                                                          |
| `wait_for_selector` | `waitForSelector` | str  | `None` (omitted) | CSS selector or text to wait for on the page before returning the result, up to 500 characters.                                                                                                                                |
| `geo_code`          | `geoCode`         | str  | `None` (omitted) | Two-letter country code to load the page from, sent in lowercase.                                                                                                                                                              |
| `max_age`           | `maxAge`          | int  | `0`              | Return a cached result of the same request when it is newer than the selected age. A cached result costs the same tokens as the original scrape.                                                                               |
| `max_retries`       | `maxRetries`      | int  | `None` (omitted) | Maximum number of retries, as a nonnegative integer. Omit this parameter for no limit.                                                                                                                                         |

The request uses `browserRendering=true`, `html=false`, `markdown=false`, and `saveResult=true`; these are not service parameters. `screenshot` defaults to `full` and also accepts `top` or a `WIDTHxHEIGHT[-ZOOM]` viewport. The API still includes the page HTML in the response.

#### Example

```python
import asyncio
from mrscraper import MrScraper

async def main():
    client = MrScraper()
    result = await client.get_screenshot('https://example.com', screenshot='top', timeout=120)
    print(result["data"])

asyncio.run(main())
```

#### Response

The response body is JSON containing a base64 PNG screenshot and the page HTML, which the API includes even though html=false is sent.

**Success response**

```json
{
  "status_code": 200,
  "data": {
    "html": "<html>...</html>",
    "screenshot": "BASE64_PNG_DATA"
  },
  "headers": {
    "content-type": "application/json; charset=utf-8"
  }
}
```

### Scrape brand

#### Description

Extract a website's colors, typography, logos, and social links as JSON.

#### Parameters

| Parameter | HTTP field | Type | Default  | Description                                        |
| --------- | ---------- | ---- | -------- | -------------------------------------------------- |
| `url`     | `url`      | str  | Required | Absolute HTTP or HTTPS URL of the page to process. |

The HTTP deadline is fixed at 120 seconds. It is not a service parameter.

The request uses `action=brand-scraping` and `bundle=none`; page controls are not accepted.

#### Example

```python
import asyncio
from mrscraper import MrScraper

async def main():
    client = MrScraper()
    result = await client.scrape_brand('https://example.com')
    print(result["data"])

asyncio.run(main())
```

#### Response

The API body contains message and a data object with job_id, status, url, final_url, brand, and error. Brand details are available at data.data.brand in the response envelope.

**Success response**

```json
{
  "status_code": 200,
  "data": {
    "data": {
      "job_id": "JOB_ID",
      "status": "succeeded",
      "url": "https://example.com",
      "final_url": "https://example.com",
      "brand": {
        "name": "Example brand",
        "colors": {
          "background": "#ffffff",
          "text": "#222222"
        },
        "typography": {
          "body": {
            "font_family": "Example font"
          }
        }
      },
      "error": null,
      "bundle_url": null
    },
    "message": "Example response"
  },
  "headers": {
    "content-type": "application/json"
  }
}
```

### Scrape JSON

#### Description

Extract structured JSON from a page using a natural-language prompt. Append Json Schema: and a JSON schema to shape the output.

#### Parameters

| Parameter           | HTTP field         | Type | Default                                       | Description                                                                                                                                                                                     |
| ------------------- | ------------------ | ---- | --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `url`               | `url`              | str  | Required                                      | Absolute HTTP or HTTPS URL of the page to process.                                                                                                                                              |
| `prompt`            | `prompt`           | str  | `"Extract all data as complete as possible."` | Instructions describing the data to extract. Append Json Schema: and a JSON schema to shape the output.                                                                                         |
| `html`              | `html`             | bool | `True`                                        | Whether to include the page HTML in the response.                                                                                                                                               |
| `browser_rendering` | `browserRendering` | bool | `None` (omitted)                              | Whether to load the page in a browser: true always does and false never does. Omit it to load the page without a browser first and switch to a browser automatically if the request is blocked. |
| `timeout`           | `timeout`          | int  | `300`                                         | Maximum seconds to wait for the scrape, from 1 to 330. The HTTP request allows 30 additional seconds.                                                                                           |
| `warm_start`        | `warmStart`        | bool | `False`                                       | Whether to open the site's home page first to warm the session before loading the target URL.                                                                                                   |
| `block_resources`   | `blockResources`   | bool | `False`                                       | Whether to block images, fonts, and stylesheets while loading the page.                                                                                                                         |
| `wait_for_selector` | `waitForSelector`  | str  | `None` (omitted)                              | CSS selector or text to wait for on the page before returning the result, up to 500 characters.                                                                                                 |
| `geo_code`          | `geoCode`          | str  | `None` (omitted)                              | Two-letter country code to load the page from, sent in lowercase.                                                                                                                               |
| `max_age`           | `maxAge`           | int  | `0`                                           | Return a cached result of the same request when it is newer than the selected age. A cached result costs the same tokens as the original scrape.                                                |
| `max_retries`       | `maxRetries`       | int  | `None` (omitted)                              | Maximum number of retries, as a nonnegative integer. Omit this parameter for no limit.                                                                                                          |
| `screenshot`        | `screenshot`       | bool | `False`                                       | Whether to include a base64 screenshot in the response.                                                                                                                                         |

The request uses `agent=general`, `saveResult=true`, and GET. If the encoded URL exceeds 8,000 characters, it switches to POST with `url`, `prompt`, and `agent` in the body; page controls remain in the query.

#### Example

```python
import asyncio
from mrscraper import MrScraper

async def main():
    client = MrScraper()
    result = await client.scrape_json('https://example.com', prompt='Extract the first 2 items with title and price. Json Schema: {"type":"array","items":{"type":"object","properties":{"title":{"type":"string"},"price":{"type":"string"}},"required":["title","price"]}}', browser_rendering=True)
    print(result["data"])

asyncio.run(main())
```

#### Response

Extraction results are in the API body's data field and follow the requested schema. Response metadata includes thread_id, token_usage, status, error, runtime, and cookies. html contains the page HTML unless disabled; markdown and screenshot can be empty strings.

**Success response**

```json
{
  "status_code": 200,
  "data": {
    "success": true,
    "data": [
      {
        "title": "Example item",
        "price": "10.00"
      }
    ],
    "thread_id": "THREAD_ID",
    "token_usage": 1,
    "html": "<html>...</html>",
    "markdown": "",
    "screenshot": "",
    "status": "Results ready",
    "error": "",
    "runtime": 1.23,
    "cookies": []
  },
  "headers": {
    "content-type": "application/json"
  }
}
```

### Web search

#### Description

Search the web and return ranked results with titles, URLs, descriptions, and sources.

#### Parameters

| Parameter     | HTTP field   | Type | Default          | Description                                                                                       |
| ------------- | ------------ | ---- | ---------------- | ------------------------------------------------------------------------------------------------- |
| `query`       | `query`      | str  | Required         | Search query text, trimmed before sending, containing 1 to 1000 characters.                       |
| `country`     | `country`    | str  | `None` (omitted) | Two-letter country code to search from, sent in lowercase.                                        |
| `num_results` | `numResults` | int  | `10`             | Number of search results to request, as an integer from 10 to 100. Fewer results may be returned. |

The HTTP deadline is fixed at 120 seconds. It is not a service parameter.

The request uses `action=websearch`. `country` is omitted unless set, so the API searches from the United States.

#### Example

```python
import asyncio
from mrscraper import MrScraper

async def main():
    client = MrScraper()
    result = await client.web_search('site:example.com documentation', country='id', num_results=20)
    print(result["data"])

asyncio.run(main())
```

#### Response

The API body contains success, message, a data array, and tokenUsage. Each result includes rank, title, url, description, and source.

**Success response**

```json
{
  "status_code": 200,
  "data": {
    "success": true,
    "message": "Example response",
    "data": [
      {
        "rank": 1,
        "title": "Example result",
        "url": "https://example.com",
        "description": "Example result description.",
        "source": "example.com"
      }
    ],
    "tokenUsage": 1
  },
  "headers": {
    "content-type": "application/json; charset=utf-8"
  }
}
```

## Response format

Successful services use an envelope containing `status_code`, `data`, and `headers`. The `data` field contains the API response body; its field names are not converted to the SDK's naming style. Status preserves the complete body without adding summary fields.

```json
{
  "status_code": 200,
  "data": "<html><body>Example page content...</body></html>",
  "headers": {
    "content-type": "text/html; charset=utf-8"
  }
}
```

Responses are Python dictionaries. JSON becomes Python values, text remains `str`, and binary remains `bytes`. Sensitive response headers are removed for status.

## Error handling

Authentication failures raise `AuthenticationError`; other HTTP error statuses raise `APIError`; connection and timeout failures raise `NetworkError`. `APIError.status_code` contains the HTTP status when available. Invalid arguments raise `ValueError` or `TypeError` before the request.

```python
import asyncio
from mrscraper import MrScraper, APIError, AuthenticationError, NetworkError

async def main():
    try:
        await MrScraper().scrape_html("https://example.com")
    except AuthenticationError as error:
        print("Check authentication:", error)
    except APIError as error:
        print(error.status_code, error)
    except NetworkError as error:
        print("Request failed:", error)

asyncio.run(main())
```

## Integration features

### Configuration

All methods are coroutines and must be awaited. Examples use `asyncio.run(main())`; inside a notebook with an active event loop, use `await main()` instead. Keyword dictionaries can be unpacked with `**payload`. Optional controls set to `None` are omitted; explicit `False` and `0` are preserved.

### Advanced usage

Reuse an HTTP connection pool by passing `http_client=httpx.AsyncClient(...)`. You manage the supplied client's lifetime; the SDK creates and closes its own client when one is not supplied.

```python
import asyncio
import httpx
from mrscraper import MrScraper

async def main():
    async with httpx.AsyncClient() as http_client:
        client = MrScraper(http_client=http_client)
        print((await client.status())["data"])
        print((await client.scrape_markdown("https://example.com"))["data"])

asyncio.run(main())
```

The SDK applies each service's HTTP deadline even when a shared client is supplied.

### Troubleshooting

Check token precedence when authentication fails. Use snake_case argument names rather than HTTP camelCase names. Page timeouts must be integers from 1 to 330; search does not accept a timeout argument. Inspect the raw API body before selecting nested fields.

## Development and testing

### Automated checks

The automated suite checks service behavior without production API calls.

```bash
python -m pip install -e . pytest pytest-asyncio httpx ruff mypy
python -m pytest -m 'not integration' -q
ruff check src tests
mypy src
```

### Manual checks

The following commands call the live API using your credentials and consume quota.

```bash
python file.py status
python file.py scrape-html --url https://example.com
python file.py web-search --query "site:example.com documentation"
```

## License

MIT. See [LICENSE](./LICENSE).
