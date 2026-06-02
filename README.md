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

Fetch the rendered HTML of a page using the MrScraper stealth browser. Handles JavaScript rendering, bot detection evasion, and optional geolocation proxying.

```python
result = await client.fetch_html(
    "https://stockx.com/air-jordan-1-retro-low-og-chicago-2025",
    geo_code="US",
    timeout=120,
    block_resources=False,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | *(required)* | Target URL to scrape |
| `timeout` | `int` | `120` | Maximum seconds to wait for the page to load |
| `geo_code` | `str` | `"US"` | ISO country code for proxy-based geolocation (e.g. `"US"`, `"GB"`, `"ID"`, `"SG"`) |
| `block_resources` | `bool` | `False` | When `True`, blocks images, CSS, and fonts to speed up the request |

**Returns:** `dict` with keys `status_code`, `data` (raw HTML string), and `headers`.

---

### Create an AI scraper

Create an AI-powered scraper using natural-language instructions and run it immediately. No CSS selectors required.

```python
result = await client.create_scraper(
    url="https://example.com/products",
    message="Extract all product names, prices, and ratings",
    agent="listing",          # "general" | "listing" | "map"
    proxy_country="US",
)
scraper_id = result["data"]["data"]["scraperId"]
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | *(required)* | Target URL to scrape |
| `message` | `str` | *(required)* | Natural-language description of what to extract (e.g. `"Extract all product names and prices"`) |
| `agent` | `"general"` \| `"listing"` \| `"map"` | `"general"` | AI agent type (see table below) |
| `proxy_country` | `str \| None` | `None` | ISO country code for proxy selection (e.g. `"US"`, `"GB"`, `"SG"`) |
| `max_depth` | `int` | `2` | *(map agent only)* Crawl depth from the start URL. `0` = start URL only |
| `max_pages` | `int` | `50` | *(map agent only)* Maximum number of pages to process |
| `limit` | `int` | `1000` | *(map agent only)* Maximum number of records to extract |
| `include_patterns` | `str` | `""` | *(map agent only)* `\|\|`-separated URL regex patterns to include when following links |
| `exclude_patterns` | `str` | `""` | *(map agent only)* `\|\|`-separated URL regex patterns to skip when following links |

| Agent | Best used for |
|-------|---------------|
| `"general"` | Default; handles almost any page |
| `"listing"` | Product listings, job boards, search results |
| `"map"` | Crawling all sub-pages / sitemaps of a site |

**Returns:** `dict` with keys `status_code`, `data` (scraper info including the scraper ID), and `headers`.

---

### Rerun a scraper on a new URL

Reuse the extraction logic from a previously created AI scraper on any compatible URL.

```python
result = await client.rerun_scraper(
    scraper_id=scraper_id,
    url="https://example.com/products?page=2",
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `scraper_id` | `str` | *(required)* | ID of the scraper to rerun (from `create_scraper`) |
| `url` | `str` | *(required)* | Target URL — can be the original URL or a different page |
| `max_depth` | `int` | `2` | *(map agent only)* Crawl depth from the start URL |
| `max_pages` | `int` | `50` | *(map agent only)* Maximum number of pages to process |
| `limit` | `int` | `1000` | *(map agent only)* Maximum number of records to extract |
| `include_patterns` | `str` | `""` | *(map agent only)* `\|\|`-separated URL regex patterns to include |
| `exclude_patterns` | `str` | `""` | *(map agent only)* `\|\|`-separated URL regex patterns to skip |

**Returns:** `dict` with keys `status_code`, `data`, and `headers`.

---

### Bulk rerun on multiple URLs (AI scraper)

Rerun an existing AI scraper on multiple URLs in a single batch request. More efficient than calling `rerun_scraper` in a loop — all URLs are dispatched in parallel server-side.

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

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `scraper_id` | `str` | *(required)* | ID of the scraper to rerun (from `create_scraper`) |
| `urls` | `list[str]` | *(required)* | List of target URLs. Must contain at least one URL |

**Returns:** `dict` with keys `status_code`, `data`, and `headers`.

---

### Rerun a manually configured scraper

Rerun a scraper that was created manually through the MrScraper dashboard (with custom CSS selectors or XPath rules) on a new URL. Must **not** be an AI scraper. Find your scraper ID at https://app.mrscraper.com.

```python
result = await client.rerun_manual_scraper(
    scraper_id="SCRAPER_ID",
    url="https://example.com/products/new-item",
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `scraper_id` | `str` | *(required)* | ID of the manual scraper (found in the MrScraper dashboard) |
| `url` | `str` | *(required)* | Target URL — page structure should match the original scraper's target for selectors to work |

**Returns:** `dict` with keys `status_code`, `data`, and `headers`.

---

### Bulk rerun manual scraper on multiple URLs

Rerun a manually configured scraper on multiple URLs in a single batch. All URLs are processed in parallel server-side. Find your scraper ID at https://app.mrscraper.com.

```python
result = await client.bulk_rerun_manual_scraper(
    scraper_id="SCRAPER_ID",
    urls=[
        "https://www.example.com/products/item1",
        "https://www.example.com/products/item2",
        "https://www.example.com/products/item3",
    ],
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `scraper_id` | `str` | *(required)* | ID of the manual scraper (from the MrScraper dashboard). Must be a scraper created manually via the web interface, not an AI scraper |
| `urls` | `list[str]` | *(required)* | List of target URLs. Each URL is processed independently using the scraper's logic |

**Returns:** `dict` with keys `status_code`, `data` (bulk job info including job ID and status), and `headers`.

---

### Fetch Google SERP

Fetch Google search engine results pages (SERP) synchronously.

```python
result = await client.fetch_google_serp(
    "https://www.google.com/search?q=iphone+17",
    raw=True,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | *(required)* | Full Google search URL to scrape (e.g. `"https://www.google.com/search?q=iphone+17"`) |
| `raw` | `bool` | `True` | When `True`, return the raw SERP payload |
| `timeout` | `float` | `600.0` | Maximum seconds to wait for the request |

**Returns:** `dict` with keys `status_code`, `data`, and `headers`.

---

### Retrieve results

Fetch previously stored scraping results with pagination, sorting, and filtering.

```python
# All results (paginated)
results = await client.get_all_results(
    sort_field="updatedAt",
    sort_order="DESC",
    page_size=20,
    page=1,
    search="product",
    date_range_column="updatedAt",
    start_at="2024-01-01",
    end_at="2024-01-31",
)

# A specific result by ID
result = await client.get_result_by_id("RESULT_ID")
```

#### `get_all_results` parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sort_field` | `str` | `"updatedAt"` | Field to sort by. Options: `"createdAt"`, `"updatedAt"`, `"id"`, `"type"`, `"url"`, `"status"`, `"error"`, `"tokenUsage"`, `"runtime"` |
| `sort_order` | `"ASC"` \| `"DESC"` | `"DESC"` | Sort direction |
| `page_size` | `int` | `10` | Number of results per page |
| `page` | `int` | `1` | Page number (1-indexed) |
| `search` | `str \| None` | `None` | Free-text search query across result fields |
| `date_range_column` | `str \| None` | `None` | Column name to filter by date range (e.g. `"updatedAt"`, `"createdAt"`) |
| `start_at` | `str \| None` | `None` | ISO-8601 start date for the date range filter (e.g. `"2024-01-01"`) |
| `end_at` | `str \| None` | `None` | ISO-8601 end date for the date range filter (e.g. `"2024-01-31"`) |

**Returns:** `dict` with keys `status_code`, `data` (paginated results and pagination metadata), and `headers`.

#### `get_result_by_id` parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `result_id` | `str` | *(required)* | Unique identifier of the result (returned by scraper execution methods and `get_all_results`) |

**Returns:** `dict` with keys `status_code`, `data` (complete result object), and `headers`.

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
