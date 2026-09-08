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
    html=True,
    geo_code="US",
    timeout=120,
    browser_rendering=True,
    super_mode=False,
    use_proxy=True,
    wait_for_selector="body",
    home_page=True,
    block_resources=False,
    headers={"accept-language": "en-US,en;q=0.9"},
)
```

Set `home_page=True` when a site is more reliable after first visiting its
root page. This lets the browser establish cookies and session state before
opening the target URL, which can help with some anti-bot checks.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | *(required)* | Target URL to scrape |
| `timeout` | `int` | `120` | Maximum seconds to wait for the page to load |
| `geo_code` | `str` | `"US"` | ISO country code for proxy-based geolocation (e.g. `"US"`, `"GB"`, `"ID"`, `"SG"`) |
| `proxy_country` | `str \| None` | `None` | Compatibility proxy-country field sent as `proxyCountry` |
| `block_resources` | `bool \| None` | `False` | When `True`, blocks images, CSS, and fonts to speed up the request |
| `browser_rendering` | `bool \| None` | `None` | `True` enables a browser, `False` disables it, and `None` allows automatic fallback |
| `super_mode` | `bool` | `False` | Use real-device routing independently of browser rendering |
| `use_proxy` | `bool` | `True` | Allow the service to use a configured proxy |
| `proxy` | `str \| None` | `None` | Custom proxy string (`username:password@host:port`) |
| `wait_for_selector` | `str \| None` | `None` | CSS selector to wait for before returning content |
| `home_page` | `bool` | `False` | Visit the site's root page first to establish cookies/session state; this can improve reliability on some sites with anti-bot checks |
| `bypass_proxy` | `bool` | `False` | Enable proxy bypass/resource-blocking behavior |
| `cookie_jar` | `str \| None` | `None` | Cookie configuration string |
| `headers` | `dict[str, str] \| str \| None` | `None` | Target request headers as a dictionary or JSON string |
| `max_retries` | `int` | `3` | Maximum Web Unblocker retry count; `0` disables retries |
| `token_cap` | `int \| None` | `None` | Optional retry-token budget |
| `stream` | `bool \| None` | `None` | Ask the API for a streamed response; the SDK buffers it |
| `discard_token_secret` | `str` | `""` | Value for the `x-discard-token-secret` HTTP header |

**Returns:** `dict` with keys `status_code`, `data` (raw HTML string), and `headers`.

`fetch_html` calls `POST https://api.mrscraper.com` and maps the Python
snake_case options to camelCase fields in the JSON request body.

---

### Create an AI scraper

Create an AI-powered scraper using natural-language instructions and run it immediately. No CSS selectors required.

```python
result = await client.create_scraper(
    url="https://example.com/products",
    message="Extract all product names, prices, and ratings",
    agent="listing",          # "general" | "listing" | "map"
    mode="Super",             # "Cheap" | "Super"
    proxy_country="US",
    max_pages=5,
)
scraper_id = result["data"]["data"]["scraperId"]
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | *(required)* | Target URL to scrape |
| `message` | `str` | *(required)* | Natural-language description of what to extract (e.g. `"Extract all product names and prices"`) |
| `agent` | `"general"` \| `"listing"` \| `"map"` | `"general"` | AI agent type (see table below) |
| `mode` | `"Cheap"` \| `"Super"` \| `None` | `None` | Optional backend execution tier |
| `schema_prompt` | `dict \| None` | `None` | Best-effort JSON Schema output-shape guidance for general/listing |
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

Reuse the extraction logic from a previously created AI scraper on any compatible URL. The saved scraper determines the agent type, so pass only the parameters supported by that agent.

```python
# General agent scraper
general_result = await client.rerun_scraper(
    scraper_id=general_scraper_id,
    url="https://example.com/products?page=2",
    proxy_country="US",
    home_page=False,
    markdown=True,
)

# Listing agent scraper
listing_result = await client.rerun_scraper(
    scraper_id=listing_scraper_id,
    url="https://example.com/products",
    max_pages=5,
    home_page=False,
    markdown=True,
)

# Map agent scraper
map_result = await client.rerun_scraper(
    scraper_id=map_scraper_id,
    url="https://example.com/docs",
    max_depth=3,
    max_pages=100,
    limit=500,
    include_patterns=r"^https://example\.com/docs",
    exclude_patterns=r"/login|/account",
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `scraper_id` | `str` | *(required)* | ID of the scraper to rerun (from `create_scraper`) |
| `url` | `str` | *(required)* | Target URL — can be the original URL or a different page |
| `max_depth` | `int` | `2` | **Map agent only.** Maximum link depth from the start URL |
| `max_pages` | `int` | `50` | **Listing or map agent only.** Maximum pages to process |
| `limit` | `int` | `1000` | **Map agent only.** Maximum discovered results |
| `include_patterns` | `str` | `""` | **Map agent only.** URL inclusion expression |
| `exclude_patterns` | `str` | `""` | **Map agent only.** URL exclusion expression |
| `proxy_country` | `str \| None` | `None` | **General/listing agent only.** Proxy country override |
| `max_retries` | `int \| None` | `None` | Optional maximum retry count |
| `timeout` | `int \| None` | `None` | **Listing agent only.** Backend timeout in seconds |
| `home_page` | `bool` | `False` | **General/listing agent only.** Visit the home page before the target |
| `html` | `bool` | `False` | **General/listing agent only.** Include HTML output |
| `markdown` | `bool` | `False` | **General/listing agent only.** Include Markdown output |
| `screenshot` | `bool` | `False` | **General/listing agent only.** Include a screenshot |
| `bypass_proxy` | `bool` | `False` | **General/listing agent only.** Enable proxy bypass/resource blocking |
| `wait_for_selector` | `str \| None` | `None` | **General/listing agent only.** Wait for a CSS selector |
| `render_javascript` | `bool` | `False` | **General/listing agent only.** Execute page JavaScript |
| `use_proxy` | `bool` | `True` | **General/listing agent only.** Allow proxy use |
| `proxy` | `str \| None` | `None` | **General/listing agent only.** Custom proxy string |
| `return_cookies` | `bool` | `False` | **General/listing agent only.** Include returned cookies |
| `show_modal` | `bool` | `False` | **General/listing agent only.** Enable modal-related output |
| `stream` | `bool` | `False` | **Listing agent only.** Request streamed processing |

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
    proxy_country="ID",
    use_proxy=True,
    bypass_proxy=True,
    home_page=True,
    markdown=True,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `scraper_id` | `str` | *(required)* | ID of the manual scraper (found in the MrScraper dashboard) |
| `url` | `str` | *(required)* | Target URL — page structure should match the original scraper's target for selectors to work |
| `proxy` | `str \| None` | `None` | Custom proxy string |
| `proxy_country` | `str \| None` | `None` | Two-character proxy country code |
| `max_retries` | `int` | `3` | Maximum retry count |
| `return_cookies` | `bool` | `False` | Include cookies in the result |
| `global_domain` | `bool` | `True` | Apply returned cookies to the global domain |
| `use_proxy` | `bool` | `True` | Allow proxy use |
| `bypass_proxy` | `bool` | `True` | Enable proxy bypass/resource blocking |
| `home_page` | `bool` | `False` | Visit the site home page before the target |
| `home_page_timeout` | `int \| None` | `10` | Home-page navigation timeout in seconds |
| `html` | `bool \| None` | `False` | Include HTML output |
| `markdown` | `bool \| None` | `False` | Include Markdown output |
| `screenshot` | `str \| None` | `None` | Optional screenshot mode |
| `cookie_jar` | `str \| None` | `None` | Cookie configuration string |
| `browser_flags` | `dict \| None` | `None` | Browser configuration flags |
| `token_cap` | `int \| None` | `None` | Retry-token budget |
| `stream` | `bool \| None` | `None` | Request streamed processing |
| `timeout` | `float \| None` | `None` | Optional scraper timeout in seconds |

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
    "iphone 17",
    raw=False,
    region="id",
    language="id",
    page=2,
    format="json",
    render_js=False,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | *(required)* | Google query text or full Google search URL. The name remains `url` for compatibility |
| `raw` | `bool` | `True` | Deprecated compatibility alias for `format="html"`; takes precedence over `format` |
| `region` | `str \| None` | `None` | Result country; overrides `gl` parsed from a Google URL |
| `language` | `str \| None` | `None` | Result language; overrides `hl` parsed from a Google URL |
| `page` | `int \| None` | `None` | One-based result page; overrides a page derived from `start` |
| `format` | `"json"` \| `"html"` | `"json"` | Parsed JSON or raw result-page HTML |
| `render_js` | `bool` | `False` | Render JavaScript-dependent SERP features |
| `timeout` | `float` | `600.0` | Maximum seconds to wait for the request |

**Returns:** `dict` with keys `status_code`, `data`, and `headers`.

This method now uses `POST /api/google/serp/v2/sync`. For new code, pass
`raw=False` and select the response with `format`. Existing calls that omit
`raw` continue to request raw HTML.

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
    scraper_id="SCRAPER_ID",
    status="Finished",
    type="Rerun-AI",
    url="https://example.com/products?page=2",
)

# A specific result by ID
result = await client.get_result_by_id("RESULT_ID", include_html=False)
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
| `scraper_id` | `str \| None` | `None` | Exact saved scraper ID filter |
| `status` | `str \| None` | `None` | Exact result status filter |
| `type` | `str \| None` | `None` | Exact result type filter (e.g. `"Rerun-AI"`) |
| `url` | `str \| None` | `None` | Exact stored target URL filter |

**Returns:** `dict` with keys `status_code`, `data` (paginated results and pagination metadata), and `headers`.

#### `get_result_by_id` parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `result_id` | `str` | *(required)* | Unique identifier of the result (returned by scraper execution methods and `get_all_results`) |
| `include_html` | `bool` | `True` | Include stored HTML; use `False` for a smaller response |

**Returns:** `dict` with keys `status_code`, `data` (complete result object), and `headers`.

---

### Retrieve account and analytics status

The account and analytics APIs exposed by the CLI are also available directly:

```python
account = await client.get_subscription_account()

analytics = await client.get_analytic_statuses(
    domain="example.com",
    start_date="2026-09-01 00:00:00",
    end_date="2026-09-07 00:00:00",
    action="fetch",
    api_token_name="production",
)
```

`get_subscription_account()` returns subscription and token-usage information.
`get_analytic_statuses()` returns request-outcome analytics for the supplied
domain and date range.

---

## Manual API testing

[`examples/manual_test.py`](examples/manual_test.py) provides one command for
every public SDK method. It makes real API requests, so run one command at a
time and be aware that scraping operations may consume account credits. Full
responses are saved to `manual_results/`; the terminal only shows a short
preview.

Install the local SDK and set your token first:

```bash
python -m pip install -e .
export MRSCRAPER_API_TOKEN="YOUR_TOKEN"
```

Use `$env:MRSCRAPER_API_TOKEN="YOUR_TOKEN"` instead of `export` in PowerShell.

Run any individual method:

```bash
# Fetch methods
python examples/manual_test.py fetch_html --url "https://books.toscrape.com/" --html
python examples/manual_test.py fetch_html --url "https://example.com/page" --home-page
python examples/manual_test.py fetch_google_serp --query "python web scraping"

# Create a general, listing, or map agent scraper
python examples/manual_test.py create_scraper --agent general
python examples/manual_test.py create_scraper --agent listing --max-pages 5
python examples/manual_test.py create_scraper --agent map --max-depth 1 --max-pages 5

# Rerun an existing AI scraper using parameters for its saved agent type
python examples/manual_test.py rerun_scraper --agent general --scraper-id "AI_SCRAPER_ID"
python examples/manual_test.py rerun_scraper --agent listing --scraper-id "AI_SCRAPER_ID" --max-pages 5
python examples/manual_test.py rerun_scraper --agent map --scraper-id "AI_SCRAPER_ID" --max-depth 1 --max-pages 5

# AI and manual bulk reruns
python examples/manual_test.py bulk_rerun_ai_scraper --scraper-id "AI_SCRAPER_ID" --urls "https://example.com/1" "https://example.com/2"
python examples/manual_test.py rerun_manual_scraper --scraper-id "MANUAL_SCRAPER_ID" --url "https://example.com/1"
python examples/manual_test.py bulk_rerun_manual_scraper --scraper-id "MANUAL_SCRAPER_ID" --urls "https://example.com/1" "https://example.com/2"

# Results, account, and analytics
python examples/manual_test.py get_all_results --page-size 5
python examples/manual_test.py get_result_by_id --result-id "RESULT_ID"
python examples/manual_test.py get_subscription_account
python examples/manual_test.py get_analytic_statuses --domain "example.com" --start-date "2026-09-01 00:00:00" --end-date "2026-09-07 23:59:59"
```

Run `python examples/manual_test.py <method> --help` to see the options for a
specific method. For example, use the scraper ID returned by `create_scraper`
with the AI rerun commands, and obtain result IDs through `get_all_results`.

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
