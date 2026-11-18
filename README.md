# MrScraper Python SDK

![](./mrscraper.jpeg)

Seven services matching the [MrScraper CLI](https://github.com/mrscraper-com/cli).

| Service | Method | Purpose |
| --- | --- | --- |
| `account` | `account` | Account, subscription, quota, and rate limits |
| `scrape-html` | `scrape_html` | Raw page HTML |
| `scrape-markdown` | `scrape_markdown` | Clean Markdown; optional HTML |
| `get-screenshot` | `get_screenshot` | Full-page or top-viewport base64 screenshot |
| `scrape-brand` | `scrape_brand` | Brand data as JSON |
| `scrape-json` | `scrape_json` | Structured extraction using a prompt |
| `web-search` | `web_search` | Ranked web search results |

## Install and use

Requires Python 3.9+. Obtain a token from [the app](https://app.mrscraper.com).

```bash
python -m pip install -U mrscraper-sdk
export MRSCRAPER_API_TOKEN="YOUR_TOKEN"
```

```python
import asyncio
from mrscraper import MrScraper

async def main():
    client = MrScraper()  # or MrScraper(token="YOUR_TOKEN")
    print((await client.account())["data"])
    html = await client.scrape_html("https://books.toscrape.com/")
    markdown = await client.scrape_markdown("https://books.toscrape.com/", html=True)
    screenshot = await client.get_screenshot("https://example.com", screenshot="top")
    brand = await client.scrape_brand("https://mrscraper.com")
    data = await client.scrape_json("https://books.toscrape.com/", prompt="Extract titles and prices")
    results = await client.web_search("web scraping", country="id", num_results=20)
    print(results["data"])

asyncio.run(main())
```

All methods are async. The client reads `MRSCRAPER_API_TOKEN` or `MRSCRAPER_API_KEY`. Pass `http_client=` to reuse an `httpx.AsyncClient`; otherwise the SDK closes its own client after each call.

Every response has `status_code`, `data`, and `headers`. JSON becomes Python values; HTML and other text remain strings; binary data remains bytes. Combined outputs retain the upstream JSON structure. Account returns a safe summary containing `subscription_status`, `enterprise`, `token_usage`, `token_limit`, `token_remaining`, `usage_percent`, `rate_limit`, `rate_ttl`, `auto_renew`, `ends_at`, and `user` (`name`, `email`, `verified`). Account accepts a positive `timeout` (default 30 seconds); API keys and billing identifiers are excluded.

`AuthenticationError` indicates missing/invalid credentials; `APIError` contains the HTTP `status_code`; `NetworkError` indicates transport failures. All inherit from `MrScraperError`.

See the [REST API reference](docs/api-reference.md) for wire examples and parameter mappings.

## Options

| Python / LangChain | Node / MCP | Default | Meaning |
| --- | --- | --- | --- |
| `timeout` | `timeout` | `300` | Page deadline in seconds, integer 1–300 |
| `geo_code` | `geoCode` | `"us"` | Country to load the page from |
| `proxy_country` | `proxyCountry` | `"us"` | Proxy server country |
| `super` | `superMode` | `False` / `false` | Use real-device routing; sent as `super` |
| `wait_until` | `waitUntil` | `"domcontentloaded"` | Also accepts `load`, `networkidle0`, `networkidle2` |
| `proxy` | `proxy` | omitted | Custom proxy URL |
| `max_retries` | `maxRetries` | omitted | Nonnegative retry limit; omission means no limit |
| `save_result` | `saveResult` | `False` / `false` | Save the result in the dashboard |
| `block_resources` | `blockResources` | `False` / `false` | Block images, fonts, and stylesheets |
| `wait_for_selector` | `waitForSelector` | omitted | Wait for a CSS selector |
| `return_cookie` | `returnCookie` | `False` / `false` | Include session cookies |
| `browser_rendering` | `browserRendering` | `False` / `false` | Enable browser rendering |

The first eight page controls apply to HTML, Markdown, screenshots, and JSON. The three loading controls (`block_resources`/`blockResources`, `wait_for_selector`/`waitForSelector`, `return_cookie`/`returnCookie`) apply to HTML, Markdown, and screenshots. Browser rendering can be selected for HTML, Markdown, and JSON; screenshots always enable it.

Markdown accepts `html=False` / `html: false`; enabling HTML forces browser rendering. Screenshots accept `screenshot="full"` or `"top"`, `html=True` / `true`, and `markdown=False` / `false`. JSON accepts a `prompt` (default `"Extract all data as complete as possible."`), `html=False` / `false`, and `screenshot=False` / `false`. JSON does not expose loading or cookie controls. Brand takes only the target URL, plus authentication in the Node SDK.

Search takes `query`, `country="us"`, and `num_results=10` / `numResults: 10` (integer 10–100). Queries are trimmed and must contain 1–1,000 characters. Countries are two ASCII letters and are sent in lowercase. Search also accepts a positive local `timeout`, default 120 seconds. This timeout is not sent upstream as a page option.

## HTTP contract

The CLI repository is the source of truth for service behavior. These are seven services, using two API hosts:

| Service | Request |
| --- | --- |
| Account | `GET https://api.app.mrscraper.com/api/v1/subscription-accounts` |
| HTML | `GET https://api.mrscraper.com?url=…&html=true&markdown=false&screenshot=false` |
| Markdown | `GET https://api.mrscraper.com?url=…&html=false&markdown=true&screenshot=false` |
| Screenshot | `GET https://api.mrscraper.com?url=…&browserRendering=true&screenshot=full&html=true&markdown=false` |
| Brand | `GET https://api.mrscraper.com?action=brand-scraping&url=…&bundle=none` |
| JSON | `GET https://api.mrscraper.com?url=…&agent=general&prompt=…&html=false&screenshot=false` |
| Web search | `GET https://api.mrscraper.com?action=websearch&query=…&country=us&numResults=10` |

JSON uses GET until the encoded URL exceeds 8,000 characters. It then uses POST with `{ "url", "prompt", "agent": "general" }` in the JSON body and page controls in the query. Append `Json Schema:` and a JSON schema to the prompt to shape the extraction.

Authentication uses headers. Credentials are never placed in the query string. Page requests allow 30 seconds beyond the page timeout for HTTP transport; brand and search default to 120 seconds. Brand returns JSON synchronously with `bundle=none`.

## Migration

This release replaces the combined `scraper_api` service with `scrape_html`, `scrape_markdown`, and `get_screenshot`, and adds public `scrape_brand` and `scrape_json`. For combined outputs use `scrape_markdown(..., html=True)` or `get_screenshot(..., html=True, markdown=True)`. The old `full_page` option becomes `screenshot="full"` or `"top"`. LangChain tool names follow `mrscraper_<service>`.

Page defaults now match the CLI: 300-second timeout, US geolocation and proxy country, rendering off unless required by a chosen service, and no explicit retry limit. Search uses `query`, `country`, and a result count; old URL/locale/raw/format options are removed. Legacy scraper job, sitemap, rerun, result, and bundle-download methods are outside this seven-service API.

## Manual testing

These commands make live calls and consume quota. Each service can be tested separately.

```bash
python -m pip install -e .
export MRSCRAPER_API_TOKEN="YOUR_TOKEN"
python file.py                          # all seven, with a pass/fail summary
python file.py account
python file.py scrape-html --url https://example.com
python file.py scrape-markdown --args '{"html":true}'
python file.py get-screenshot --args '{"screenshot":"top"}'
python file.py scrape-brand --url https://mrscraper.com
python file.py scrape-json --args '{"prompt":"Extract titles and prices"}'
python file.py web-search --query "web scraping" --args '{"country":"id","num_results":20}'
```

Responses, screenshots, and the summary are saved under `manual_results/`. `test_pypi.py` is an alias for this local checkout runner.

## Development

```bash
python -m pip install -e . pytest pytest-asyncio respx build twine
python -m pytest -m "not integration" -q
python -m build
python -m twine check dist/*
# Opt-in live suite:
MRSCRAPER_RUN_LIVE=1 python -m pytest -m integration -q
```

Version 0.10.0 is configured in `pyproject.toml` and `src/mrscraper/__init__.py`. Publish this Python SDK before LangChain 0.6.0, which depends on it.

## License

MIT © MrScraper
