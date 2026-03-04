# MrScraper Python SDK

A clean, typed Python client for the [MrScraper](https://mrscraper.com) web-scraping API.
Supports both **synchronous** and **async/await** usage.

---

## Installation

```bash
pip install mrscraper-sdk
```

Requires Python 3.10+.

---

## Authentication

Every client is initialised with your MrScraper API token.
Get yours at <https://app.mrscraper.com>.

```python
from mrscraper import MrScraperClient

client = MrScraperClient(token="atk_your_token_here")
```

---

## Quick Start

### Fetch raw HTML (stealth browser)

```python
from mrscraper import MrScraperClient

client = MrScraperClient(token="atk_your_token_here")

result = client.fetch_html(
    "https://stockx.com/air-jordan-1-retro-low-og-chicago-2025",
    geo_code="US",
    timeout=120,
    block_resources=False,
)
print(result["data"])   # raw HTML string
```

### Create an AI scraper

```python
result = client.create_scraper(
    url="https://example.com/products",
    message="Extract all product names, prices, and ratings",
    agent="listing",          # "general" | "listing" | "map"
    proxy_country="US",
)
scraper_id = result["data"]["id"]
print("Scraper ID:", scraper_id)
```

### Rerun a scraper on a new URL

```python
result = client.rerun_scraper(
    scraper_id=scraper_id,
    url="https://example.com/products?page=2",
)
```

### Bulk rerun on multiple URLs

```python
result = client.bulk_rerun_scraper(
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
result = client.rerun_manual_scraper(
    scraper_id="manual_scraper_67890",
    url="https://example.com/products/new-item",
)
```

### Retrieve results

```python
# All results (paginated)
page = client.get_all_results(
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
result = client.get_result_by_id("result_12345")
print(result["data"])
```

---

## Async usage

All methods are available on `AsyncMrScraperClient`:

```python
import asyncio
from mrscraper import AsyncMrScraperClient

async def main():
    client = AsyncMrScraperClient(token="atk_your_token_here")

    html = await client.fetch_html("https://example.com")

    scraper = await client.create_scraper(
        url="https://example.com/products",
        message="Extract product names and prices",
        agent="general",
    )

    results = await client.get_all_results(page_size=50)
    print(results["data"])

asyncio.run(main())
```

---

## API Reference

### `MrScraperClient` / `AsyncMrScraperClient`

Both clients expose the same methods.  Async methods must be awaited.

| Method | Description |
|--------|-------------|
| `fetch_html(url, *, timeout, geo_code, block_resources)` | Fetch rendered HTML via the MrScraper stealth browser |
| `create_scraper(url, message, *, agent, proxy_country, ...)` | Create & run an AI-powered scraper |
| `rerun_scraper(scraper_id, url, *, max_depth, max_pages, limit, ...)` | Rerun an AI scraper on a new URL |
| `bulk_rerun_scraper(scraper_id, urls)` | Rerun an AI scraper on multiple URLs in one batch |
| `rerun_manual_scraper(scraper_id, url)` | Rerun a manually configured scraper |
| `get_all_results(*, sort_field, sort_order, page_size, page, search, ...)` | List all results with filtering & pagination |
| `get_result_by_id(result_id)` | Fetch a single result by its ID |

All methods return a `dict` with the following keys:

| Key | Type | Description |
|-----|------|-------------|
| `status_code` | `int` | HTTP status code |
| `data` | `Any` | Parsed JSON body or raw text |
| `headers` | `dict` | Response headers |

### `create_scraper` — agent types

| Agent | Best used for |
|-------|--------------|
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
    result = client.fetch_html("https://example.com")
except AuthenticationError:
    print("Check your API token at https://app.mrscraper.com")
except APIError as e:
    print(f"API error {e.status_code}: {e}")
except NetworkError as e:
    print(f"Network problem: {e}")
```

---

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint & format
ruff check .
ruff format .

# Type check
mypy src/mrscraper
```

---

## License

MIT © MrScraper
