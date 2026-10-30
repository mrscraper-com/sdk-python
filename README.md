# MrScraper Python SDK

![](./mrscraper.jpeg)

An async Python client for [MrScraper](https://mrscraper.com) page scraping, structured extraction, brand scraping, Web Search, and account status. Requires Python 3.9+.

## Install and authenticate

Install the SDK and configure your API token:

```bash
python -m pip install --upgrade mrscraper-sdk
export MRSCRAPER_API_TOKEN="YOUR_TOKEN"
```

For local development, install this checkout with `python -m pip install -e .`.

The client reads `MRSCRAPER_API_TOKEN` automatically. You can also pass `token="YOUR_TOKEN"` to `MrScraper`. Pass `http_client=` to reuse your own `httpx.AsyncClient`; otherwise the SDK creates one per request. All public methods are async and must be awaited.

## Public methods

| Method | Purpose |
|--------|---------|
| `scraper_html(url, ...)` | Retrieve HTML |
| `scraper_markdown(url, ...)` | Retrieve Markdown |
| `get_screenshot(url, ...)` | Capture a full-page or viewport screenshot |
| `scraper_json(url, prompt=..., ...)` | Extract structured data using the general agent |
| `scraper_multiple_page(url, prompt=..., ...)` | Extract entries using the listing agent |
| `scraper_sitemap(url, ...)` | Discover URLs using the map agent |
| `scrape_brand(url, bundle="clean", ...)` | Start a brand scraping job |
| `get_brand(job_id, output=None, ...)` | Read a brand job or download an output |
| `web_search(url, ...)` | Retrieve real-time web search results |
| `account(...)` | Read account identity, subscription, quota, and rate limits |

Each method selects its output format. Public parameters do not include `html`, `markdown`, or `screenshot` flags.

### Migrating from 0.6.x

Version 0.7.0 removes the public `scraper_api` method. The shared implementation is now private as `_scraper_api`; applications should use the public method for the desired output:

| Previous call | Replacement |
|---------------|-------------|
| `client.scraper_api(url)` | `client.scraper_html(url)` |
| `client.scraper_api(url, html=False, markdown=True)` | `client.scraper_markdown(url)` |
| `client.scraper_api(url, html=False, screenshot=True)` | `client.get_screenshot(url, full_page=False)` |

Await each replacement and keep the supported page, proxy, and retry options you need. `get_screenshot(url)` defaults to a full-page screenshot. Calls that previously combined output flags must use separate format-specific calls. `web_search` and `account` remain available. Earlier `fetch_content` calls should migrate to `scraper_html`.

## HTML and Markdown

Scrape a known URL as HTML or Markdown. Common controls support JavaScript rendering, geolocation, proxies, cookies, custom target headers, and waiting for page content.

```python
import asyncio
from mrscraper import MrScraper

async def main():
    client = MrScraper()
    html = await client.scraper_html("https://www.scrapethissite.com")
    markdown = await client.scraper_markdown(
        "https://www.scrapethissite.com",
        home_page=True,
        super=True,
        proxy_country="us",
    )
    print(html["data"])
    print(markdown["data"])

asyncio.run(main())
```

Both methods return a response with `status_code`, `data`, and `headers` keys. JSON responses become Python values, text responses remain strings, and binary downloads remain bytes in `data`.

### Common scraping options

These options apply to the URL-based scraping methods. `get_brand` instead accepts only a job ID, optional output, and its HTTP timeout.

| Option | Default | Description |
|--------|---------|-------------|
| `url` | required | Target URL |
| `timeout` | `120` | Page timeout from 1 to 300 seconds; screenshot default is `300`. HTTP deadline is 30 seconds longer. |
| `geo_code`, `proxy_country` | `"US"`, `None` | Geolocation country code and optional proxy country |
| `browser_rendering` | `None` | Force, disable, or automatically select rendering. Not exposed by `get_screenshot`, which always enables browser rendering. |
| `super` | `False` | Enable real device routing |
| `use_proxy`, `proxy` | `True`, `None` | Allow a proxy or supply `username:password@host:port` |
| `home_page` | `False` | Visit the site's root before the target page |
| `wait_for_selector`, `wait_until` | `None`, `None` | Wait for a CSS selector or page lifecycle event; screenshot `wait_until` defaults to `"domcontentloaded"` |
| `block_resources`, `bypass_proxy` | `False`, `False` | Block images, CSS, and fonts, or enable proxy bypass behavior |
| `cookie_jar`, `headers` | `None`, `None` | Cookie configuration string and target request headers (dictionary or JSON string) |
| `max_retries`, `token_cap` | `3`, `None` | Retry count and optional token cap; nonnegative values |
| `stream` | `None` | Request a streamed response, buffered by the SDK |
| `discard_token_secret` | `""` | Value for the `x-discard-token-secret` header |

Options set to `None` use the service defaults. Set `use_proxy=False` to disable proxy use.

## Get screenshot

`get_screenshot` captures a full page with browser rendering enabled. Defaults are `full_page=True`, `wait_until="domcontentloaded"`, `timeout=300`, and `max_retries=3`. Pass `full_page=False` to capture the viewport. Image responses are returned as bytes; the service may also return JSON data.

```python
result = await client.get_screenshot(
    "https://www.scrapethissite.com",
    super=True,
    proxy_country="us",
    token_cap=30,
)
# For an image response:
if isinstance(result["data"], bytes):
    from pathlib import Path
    Path("screenshot.png").write_bytes(result["data"])
```

## Structured extraction

Use `scraper_json` for one page or `scraper_multiple_page` for listing entries across pages. The agent is selected by the method and is absent from its parameters.

```python
page = await client.scraper_json(
    "https://mrscraper.com/pricing",
    prompt="Extract every plan's name, price, and features.",
)
entries = await client.scraper_multiple_page(
    "https://books.toscrape.com",
    max_pages=3,
)
```

`scraper_json` defaults to the prompt `"Extract all data as complete as possible."`. `scraper_multiple_page` defaults to `"Extract all entry data as complete as possible."` and `max_pages=3`. Pass your own `prompt` to describe the data to extract.

## Sitemap discovery

`scraper_sitemap` discovers site URLs with defaults `max_depth=2`, `max_pages=3`, and `limit=1000`. Use optional `include_patterns` and `exclude_patterns` strings to filter URLs. Pattern strings, including regex backslashes, are preserved unchanged.

```python
result = await client.scraper_sitemap(
    "https://docs.mrscraper.com",
    max_depth=2,
    max_pages=3,
    limit=1000,
    include_patterns=r"/docs/.*|/reference/.*",
    exclude_patterns=r"\.(png|jpg)$",
)
```

## Brand scraping

`scrape_brand` starts a brand scraping job for the given `url`. `bundle` accepts `"clean"` (default), `"full"`, or `"none"`. Use the job ID from the response with `get_brand` to read the job later or download an output.

```python
job = await client.scrape_brand("https://www.brooksrunning.com", bundle="clean")
print(job["data"])  # Read the returned job ID.

brand = await client.get_brand("YOUR_JOB_ID")
bundle = await client.get_brand("YOUR_JOB_ID", output="bundle")
from pathlib import Path
Path("brand.zip").write_bytes(bundle["data"])
```

`get_brand(job_id)` reads a brand job and has a 600-second timeout by default. Omit `output` for job data or select `"html"`, `"bundle"`, `"screenshot"`, or `"screenshot_full"`. JSON becomes Python values, HTML becomes text, and ZIP or image downloads remain bytes in `data`.

## Web Search

Search the web to retrieve real-time search results, including relevant website URLs, titles, descriptions, and related questions based on a given query. Results can be requested as structured JSON or HTML, with options for region, language, results page, and JavaScript rendering.

```python
import asyncio
from mrscraper import MrScraper

async def main():
    client = MrScraper()
    result = await client.web_search(
        "python web scraping",
        raw=False,
        region="us",
        language="en",
        page=1,
        format="json",
    )
    print(result["data"])

asyncio.run(main())
```

`web_search` accepts a search query as its first argument. The return value has `status_code`, `data`, and `headers` keys. `raw=True` is the default and requests HTML; set `raw=False` to use `format`.

| Option | Default | Description |
|--------|---------|-------------|
| `url` | required | The search query |
| `raw` | `True` | Request HTML when true, regardless of `format` |
| `format` | `"json"` | `"json"` or `"html"` when `raw=False` |
| `region`, `language` | `None`, `None` | Country and language |
| `page` | `None` | Results page number, starting at `1` |
| `render_js` | `False` | Render JavaScript features |
| `timeout` | `600.0` | Request timeout in seconds |

## Account status

Account returns an overview of the account associated with your API token, including user identity, subscription status, token usage, remaining quota, and rate limits. Use it to monitor consumption and check available tokens before running scraping or search jobs. The SDK returns a summary that excludes API tokens and billing identifiers.

```python
import asyncio
from mrscraper import MrScraper

async def main():
    result = await MrScraper().account(timeout=30)
    print(result["data"]["subscription_status"])
    print(result["data"]["token_remaining"])
    print(result["data"]["user"]["email"])

asyncio.run(main())
```

`account(timeout=30)` checks the account associated with the client's token.
The timeout defaults to 30 seconds and must be positive. The response has `status_code`,
`data`, and `headers` keys. `data` contains `subscription_status`, `enterprise`,
`token_usage`, `token_limit`, `token_remaining`, `usage_percent`, `rate_limit`,
`rate_ttl`, `auto_renew`, `ends_at`, and `user` (`name`, `email`, `verified`).
Remaining tokens are clamped to zero when usage exceeds the limit. API keys,
billing identifiers, and sensitive response headers are excluded.

## Try structured extraction manually

Set `MRSCRAPER_API_TOKEN` to your token from [the app](https://app.mrscraper.com), then run this example against the CIREBA property listings page. It makes one live scraping request and prints the API's data:

```bash
export MRSCRAPER_API_TOKEN="YOUR_TOKEN"
python - <<'PY'
import asyncio
import json

from mrscraper import MrScraper


async def main():
    result = await MrScraper().scraper_json(
        "http://cireba.com/cayman-islands-real-estate-listings/",
        prompt="Extract every property with its title, price, location, and URL.",
    )
    print(json.dumps(result["data"], indent=2, ensure_ascii=False))


asyncio.run(main())
PY
```

Use `scraper_multiple_page` with `max_pages=3` to extract listings across pages.

## Publishing a release

Version 0.7.1 updates documentation and tool descriptions. It is configured in `pyproject.toml` and `src/mrscraper/__init__.py`. From the repository root, validate and build the release:

```bash
python -m pip install build twine pytest pytest-asyncio respx
python -m pip install -e .
python -m pytest -m "not integration" -q
python -m build --outdir dist/manual-0.7.1
python -m twine check dist/manual-0.7.1/mrscraper_sdk-0.7.1-py3-none-any.whl dist/manual-0.7.1/mrscraper_sdk-0.7.1.tar.gz
```

Upload those two artifacts when ready to publish:

```bash
python -m twine upload --username __token__ dist/manual-0.7.1/mrscraper_sdk-0.7.1-py3-none-any.whl dist/manual-0.7.1/mrscraper_sdk-0.7.1.tar.gz
```

Twine prompts for your PyPI API token as the password. The upload command selects only version 0.7.1's wheel and source distribution. Choose a new version and update both version fields and artifact names for the next release. Documentation updates can use a patch version; new features generally use a minor version.

## Errors

`MrScraperError` is the base exception. `AuthenticationError` indicates a missing or invalid token, `APIError` carries an HTTP `status_code`, and `NetworkError` indicates a connection or timeout failure.

## Compliance & Legal Risk

Scraping login-protected pages can carry legal and compliance risks. Check the target site's terms and applicable law before automating access.

## License

MIT © MrScraper
