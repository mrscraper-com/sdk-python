# MrScraper Python SDK

![](./mrscraper.jpeg)

An async Python client for [MrScraper](https://mrscraper.com) page scraping, Web Search, and account status. Requires Python 3.9+.

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
| `scraper_api(url, ...)` | Fetch a public web page as rendered HTML, Markdown, screenshot, or a combination |
| `web_search(query, ...)` | Search the web for real-time results: website URLs, titles, and descriptions |
| `account(...)` | Read account identity, subscription, quota, and rate limits |

Every method returns a dictionary with `status_code`, `data`, and `headers` keys. JSON responses become Python values, text responses remain strings, and binary downloads remain bytes in `data`.

### Migrating from 0.7.x

Version 0.9.0 returns to three public methods. The format-specific methods from 0.7.x are no longer public; use `scraper_api` with output flags instead:

| Previous call | Replacement |
|---------------|-------------|
| `client.scraper_html(url)` | `client.scraper_api(url)` |
| `client.scraper_markdown(url)` | `client.scraper_api(url, html=False, markdown=True)` |
| `client.get_screenshot(url, full_page=False)` | `client.scraper_api(url, html=False, screenshot=True)` |
| `client.web_search(query, region="us")` | `client.web_search(query, country="us")` |

`web_search` now calls the MrScraper API with `action: "websearch"`. Its first argument is `query`, and it accepts `country` and `num_results`. The `raw`, `format`, `region`, `language`, `page`, and `render_js` options are removed.

## Scraper API

Fetch a public web page as rendered HTML, Markdown, screenshot, or a combination. Common controls support JavaScript rendering, geolocation, proxies, cookies, custom target headers, and waiting for page content.

```python
import asyncio
from mrscraper import MrScraper

async def main():
    client = MrScraper()

    html = await client.scraper_api("https://www.scrapethissite.com")
    print(html["data"])  # HTML string

    combined = await client.scraper_api(
        "https://www.scrapethissite.com",
        html=True,
        markdown=True,
        screenshot=True,
        proxy_country="us",
    )
    print(combined["data"]["markdown"])

asyncio.run(main())
```

Requesting only HTML (the default) returns the page as a string. Requesting Markdown or a screenshot returns a dictionary with an entry for each output, such as `html`, `markdown`, and `screenshot`. At least one of `html`, `markdown`, or `screenshot` must be `True`.

| Option | Default | Description |
|--------|---------|-------------|
| `url` | required | Target URL |
| `html`, `markdown`, `screenshot` | `True`, `False`, `False` | Outputs to return; combine as needed. `screenshot=True` enables browser rendering. |
| `timeout` | `120` | Page timeout from 1 to 300 seconds. HTTP deadline is 30 seconds longer. |
| `geo_code`, `proxy_country` | `"US"`, `None` | Geolocation country code and optional proxy country |
| `browser_rendering` | `None` | Force, disable, or automatically select rendering |
| `super` | `False` | Enable real device routing |
| `use_proxy`, `proxy` | `True`, `None` | Allow a proxy or supply `username:password@host:port` |
| `home_page` | `False` | Visit the site's root before the target page |
| `wait_for_selector`, `wait_until` | `None`, `None` | Wait for a CSS selector or page lifecycle event such as `"domcontentloaded"` |
| `block_resources`, `bypass_proxy` | `False`, `False` | Block images, CSS, and fonts, or enable proxy bypass behavior |
| `cookie_jar`, `headers` | `None`, `None` | Cookie configuration string and target request headers (dictionary or JSON string) |
| `max_retries`, `token_cap` | `3`, `None` | Retry count and optional token cap; nonnegative values |
| `stream` | `None` | Request a streamed response, buffered by the SDK |
| `discard_token_secret` | `""` | Value for the `x-discard-token-secret` header |

Options set to `None` use the service defaults. Set `use_proxy=False` to disable proxy use.

## Web Search

Web Search searches the web for real-time results: website URLs, titles, and descriptions.

```python
import asyncio
from mrscraper import MrScraper

async def main():
    client = MrScraper()
    result = await client.web_search(
        "e-menessaptieka.lv linkedin",
        country="us",
        num_results=10,
    )
    for item in result["data"]["data"]:
        print(item["rank"], item["title"], item["url"])

asyncio.run(main())
```

The SDK sends this request:

```bash
curl --location 'https://api.mrscraper.com' \
--header 'x-api-token: {MRSCRAPER_API_TOKEN}' \
--header 'Content-Type: application/json' \
--data '{
    "action": "websearch",
    "query": "e-menessaptieka.lv linkedin",
    "country": "us",
    "numResults": 10
}'
```

`result["data"]` contains `success`, `message`, and `data`. Each item in `data` has `rank`, `title`, `url`, `description`, and `source`.

| Option | Default | Description |
|--------|---------|-------------|
| `query` | required | The search query |
| `country` | `None` | Country code for localized results, such as `"us"`; omitted to use the service default |
| `num_results` | `10` | Number of results, an integer from 10 to 100 |
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

## Try it manually

Set `MRSCRAPER_API_TOKEN` to your token from [the app](https://app.mrscraper.com), then run the smoke test from this checkout. It calls `account`, `scraper_api`, and `web_search` against the live API and saves each response under `manual_results/`:

```bash
export MRSCRAPER_API_TOKEN="YOUR_TOKEN"
python file.py
python file.py scraper-api --url https://books.toscrape.com --markdown --screenshot
python file.py web-search --query "e-menessaptieka.lv linkedin" --country us --num-results 10
```

## Publishing a release

Version 0.9.0 is configured in `pyproject.toml` and `src/mrscraper/__init__.py`. From the repository root, validate and build the release:

```bash
python -m pip install build twine pytest pytest-asyncio respx
python -m pip install -e .
python -m pytest -m "not integration" -q
python -m build --outdir dist/manual-0.9.0
python -m twine check dist/manual-0.9.0/mrscraper_sdk-0.9.0-py3-none-any.whl dist/manual-0.9.0/mrscraper_sdk-0.9.0.tar.gz
```

Upload those two artifacts when ready to publish:

```bash
python -m twine upload --username __token__ dist/manual-0.9.0/mrscraper_sdk-0.9.0-py3-none-any.whl dist/manual-0.9.0/mrscraper_sdk-0.9.0.tar.gz
```

Twine prompts for your PyPI API token as the password. The upload command selects only version 0.9.0's wheel and source distribution. Choose a new version and update both version fields and artifact names for the next release. Documentation updates can use a patch version; new features generally use a minor version.

## Errors

`MrScraperError` is the base exception. `AuthenticationError` indicates a missing or invalid token, `APIError` carries an HTTP `status_code`, and `NetworkError` indicates a connection or timeout failure.

## Compliance & Legal Risk

Scraping login-protected pages can carry legal and compliance risks. Check the target site's terms and applicable law before automating access.

## License

MIT © MrScraper
