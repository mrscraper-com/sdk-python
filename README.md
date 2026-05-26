# MrScraper Python SDK
![](./mrscraper.jpeg)

A Simple Python SDK for the [MrScraper](https://mrscraper.com) web-scraping API.
Supports **async / await** usage.

---

## Installation

```bash
pip install mrscraper-sdk
```

Requires Python 3.9+.

---

## Authentication

Every client is initialised with your MrScraper API token.
Get yours at <https://app.mrscraper.com>.

```python
from mrscraper import MrScraper

client = MrScraper(token="MRSCRAPER_API_TOKEN")
```

---

## Quick Start

### Fetch raw HTML (stealth browser)

```python
import asyncio
from mrscraper import MrScraper

async def main():
    client = MrScraper(token="MRSCRAPER_API_TOKEN")

    result = await client.fetch_html(
        "https://stockx.com/air-jordan-1-retro-low-og-chicago-2025",
        geo_code="US",
        timeout=120,
        block_resources=False,
    )
    print(result["data"])   # raw HTML string

asyncio.run(main())
```

### Create an AI scraper

```python
result = await client.create_scraper(
    url="https://example.com/products",
    message="Extract all product names, prices, and ratings",
    agent="listing",          # "general" | "listing" | "map"
    proxy_country="US",
)
scraper_id = result["data"]["data"]["id"]
print("Scraper ID:", scraper_id)
```

### Rerun a scraper on a new URL

```python
result = await client.rerun_scraper(
    scraper_id=scraper_id,
    url="https://example.com/products?page=2",
)
```

### Bulk rerun on multiple URLs (AI scraper)

```python
result = await client.bulk_rerun_ai_scraper(
    scraper_id=scraper_id,
    urls=[
        "https://example.com/products/item1",
        "https://example.com/products/item2",
        "https://example.com/products/item3",
    ],
)
```

### Rerun a manually configured scraper

```python
result = await client.rerun_manual_scraper(
    scraper_id="manual_scraper_67890",
    url="https://example.com/products/new-item",
)
```

### Bulk rerun manual scraper on multiple URLs

```python
result = await client.bulk_rerun_manual_scraper(
    scraper_id="scraper_12345",
    urls=[
        "https://www.example.com/products/item1",
        "https://www.example.com/products/item2",
        "https://www.example.com/products/item3",
    ],
)
```

### Fetch Google SERP

```python
result = await client.fetch_google_serp(
    "https://www.google.com/search?q=iphone+17",
    raw=True,
)
print(result["data"])
```

### Retrieve results

```python
# All results (paginated)
page = await client.get_all_results(
    sort_field="updatedAt",
    sort_order="DESC",
    page_size=20,
    page=1,
    search="product",
    date_range_column="updatedAt",
    start_at="2024-01-01",
    end_at="2024-01-31",
)
print(page["data"])

# A specific result by ID
result = await client.get_result_by_id("result_12345")
print(result["data"])
```

---

## API Reference

### `MrScraper`

All methods are coroutines and must be awaited.

| Method | Description |
|--------|-------------|
| `fetch_html(url, *, timeout, geo_code, block_resources)` | Fetch rendered HTML via the MrScraper stealth browser |
| `fetch_google_serp(url, *, raw, timeout)` | Fetch Google search results (SERP) synchronously |
| `create_scraper(url, message, *, agent, proxy_country, ...)` | Create & run an AI-powered scraper |
| `rerun_scraper(scraper_id, url, *, max_depth, max_pages, limit, ...)` | Rerun an AI scraper on a new URL |
| `bulk_rerun_ai_scraper(scraper_id, urls)` | Rerun an AI scraper on multiple URLs in one batch |
| `rerun_manual_scraper(scraper_id, url)` | Rerun a manually configured scraper on a single URL |
| `bulk_rerun_manual_scraper(scraper_id, urls)` | Rerun a manual scraper on multiple URLs in one batch |
| `get_all_results(*, sort_field, sort_order, page_size, page, search, ...)` | List all results with filtering & pagination |
| `get_result_by_id(result_id)` | Fetch a single result by its ID |

All methods return a `dict` with the following keys:

| Key | Type | Description |
|-----|------|-------------|
| `status_code` | `int` | HTTP status code |
| `data` | `Any` | Parsed JSON body or raw text |
| `headers` | `dict` | Response headers |

### `bulk_rerun_manual_scraper`

Reruns a manually configured scraper on multiple URLs simultaneously in a single batch operation. This is more efficient than calling `rerun_manual_scraper` multiple times, as it processes all URLs in parallel and returns consolidated results. Ideal for scraping multiple pages, products, or articles with the same extraction logic.

| Argument | Description |
|----------|-------------|
| `scraper_id` | The ID of the manual scraper to rerun (obtained from the MrScraper dashboard). Must be a scraper created manually through the web interface, not an AI scraper. Find it at https://app.mrscraper.com |
| `urls` | A list of target URLs to scrape (required, must contain at least one URL). Each URL will be processed independently using the scraper's extraction logic. Example: `["https://example.com/page1", "https://example.com/page2"]` |

**Returns:** A dict with `status_code`, `data` (bulk job info including job ID, status, metadata; use `get_all_results` or `get_result_by_id` to fetch per-URL results), and `headers`.

**Example:**

```python
result = await client.bulk_rerun_manual_scraper(
    scraper_id="scraper_12345",
    urls=[
        "https://www.example.com/products/item1",
        "https://www.example.com/products/item2",
        "https://www.example.com/products/item3",
    ],
)
```

### `create_scraper` — agent types

| Agent | Best used for |
|-------|---------------|
| `"general"` | Default; handles almost any page |
| `"listing"` | Product listings, job boards, search results |
| `"map"` | Crawling all sub-pages / sitemaps of a site |

The `max_depth`, `max_pages`, `limit`, `include_patterns`, and `exclude_patterns`
parameters are only meaningful when `agent="map"`.

---

## Exceptions

| Exception | Raised when |
|-----------|-------------|
| `MrScraperError` | Base class for all SDK errors |
| `AuthenticationError` | API token is invalid or missing (HTTP 401) |
| `APIError` | API returned a non-2xx error; has `.status_code` attribute |
| `NetworkError` | Connection timeout or network-level failure |

```python
from mrscraper.exceptions import AuthenticationError, APIError, NetworkError

try:
    result = await client.fetch_html("https://example.com")
except AuthenticationError:
    print("Check your API token at https://app.mrscraper.com")
except APIError as e:
    print(f"API error {e.status_code}: {e}")
except NetworkError as e:
    print(f"Network problem: {e}")
```

---
## Compliance & Legal Risk
> **WARNING**
> Scraping login-protected pages carries serious legal and compliance risks. Many websites explicitly prohibit automated access in their Terms of Service, and bypassing authentication to scrape content may expose you to legal action including lawsuits, account termination, and financial penalties. By proceeding on scraping login-protected pages, you confirm that you have read and understood the target website's Terms of Service, and you fully accept all legal, financial, and ethical responsibility for your actions. 

---
## License

MIT © MrScraper
