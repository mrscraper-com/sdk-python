# MrScraper Python SDK

![](./mrscraper.jpeg)

An async Python client for [MrScraper](https://mrscraper.com) page scraping, structured extraction, brand scraping, Google SERP, and account status. Requires Python 3.9+.

## Install and authenticate

To try version 0.7.0 from this repository before publication, install the checkout:

```bash
python -m pip install -e .
export MRSCRAPER_API_TOKEN="YOUR_TOKEN"
```

After version 0.7.0 has been published, install it from PyPI with `python -m pip install --upgrade "mrscraper-sdk==0.7.0"`.

The client reads `MRSCRAPER_API_TOKEN` automatically. You can also pass `token="YOUR_TOKEN"` to `MrScraper`. Pass `http_client=` to reuse your own `httpx.AsyncClient`; otherwise the SDK creates one per request. All public methods are async and must be awaited.

The cURL examples use the same `MRSCRAPER_API_TOKEN` environment variable. They return the API response body directly, without the SDK's `status_code`, `data`, and `headers` wrapper. Examples using `--url-query` require cURL 7.87.0+; each value is URL-encoded automatically.

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
| `web_search(query_or_url, ...)` | Retrieve Google search results |
| `account(...)` | Read account identity, subscription, quota, and rate limits |

Output flags such as `html`, `markdown`, and `screenshot` are selected by each method and are absent from their public parameters. For example, `scraper_html(url)` sends `html=true` and omits both `markdown` and `screenshot` from the request.

### Migrating from 0.6.x

Version 0.7.0 removes the public `scraper_api` method. The shared implementation is now private as `_scraper_api`; applications should use the public method for the desired output:

| Previous call | Replacement |
|---------------|-------------|
| `client.scraper_api(url)` | `client.scraper_html(url)` |
| `client.scraper_api(url, html=False, markdown=True)` | `client.scraper_markdown(url)` |
| `client.scraper_api(url, html=False, screenshot=True)` | `client.get_screenshot(url, full_page=False)` |

Await each replacement and keep the supported page, proxy, and retry options you need. `get_screenshot(url)` defaults to a full-page screenshot. Calls that previously combined output flags must use separate format-specific calls. `web_search` and `account` remain available. Earlier `fetch_content` calls should migrate to `scraper_html`, and earlier `google_serp` calls should migrate to `web_search`.

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

Both methods send `POST https://api.mrscraper.com`. HTML sends only `html=true`; Markdown sends only `markdown=true`. The JSON body contains `url`, `maxRetries`, and optional `tokenCap`. The response has `status_code`, `data`, and `headers` keys. JSON responses become Python values, text responses remain strings, and binary downloads remain bytes in `data`.

HTML cURL reference with common optional controls. Remove sample settings you do not need:

```bash
curl --request POST \
  --url 'https://api.mrscraper.com' \
  --url-query "token=${MRSCRAPER_API_TOKEN}" \
  --url-query 'html=true' \
  --url-query 'timeout=120' \
  --url-query 'geoCode=US' \
  --url-query 'proxyCountry=US' \
  --url-query 'browserRendering=true' \
  --url-query 'super=true' \
  --url-query 'proxy=username:password@proxy.example.com:8080' \
  --url-query 'waitForSelector=body' \
  --url-query 'waitUntil=domcontentloaded' \
  --url-query 'warmStart=true' \
  --url-query 'blockResources=true' \
  --url-query 'bypassProxy=true' \
  --url-query 'cookieJar=domain=example.com&country=us&max_used=100&max_age=50m' \
  --url-query 'headers={"Accept-Language":"en-US","User-Agent":"Mozilla/5.0"}' \
  --url-query 'stream=false' \
  --header 'Content-Type: application/json' \
  --header 'accept: application/json' \
  --header "Authorization: Bearer ${MRSCRAPER_API_TOKEN}" \
  --header "x-api-token: ${MRSCRAPER_API_TOKEN}" \
  --header 'x-discard-token-secret: YOUR_DISCARD_TOKEN_SECRET' \
  --max-time 150 \
  --data '{"url":"https://example.com","maxRetries":3,"tokenCap":1000}'
```

The `headers` query parameter contains headers for the target page; `--header` sets headers for the MrScraper API request. `home_page` maps to `warmStart`, and `discard_token_secret` maps to `x-discard-token-secret`. Remove the sample `proxy` and `x-discard-token-secret` fields when unused. To disable proxy use, replace the custom proxy with `--url-query 'useProxy=false'`; the SDK sends that field only when `use_proxy=False`.

Markdown example:

```bash
curl --request POST \
  --url 'https://api.mrscraper.com' \
  --url-query "token=${MRSCRAPER_API_TOKEN}" \
  --url-query 'geoCode=us' \
  --url-query 'warmStart=true' \
  --url-query 'markdown=true' \
  --url-query 'super=true' \
  --url-query 'proxyCountry=us' \
  --header "x-api-token: ${MRSCRAPER_API_TOKEN}" \
  --header 'Content-Type: application/json' \
  --data '{"url":"https://www.scrapethissite.com","maxRetries":3}'
```

### Common scraping options

These options apply to the URL-based scraping methods. `get_brand` instead accepts only a job ID, optional output, and its HTTP timeout.

| Option | Default | Description |
|--------|---------|-------------|
| `url` | required | Target URL |
| `timeout` | `120` | Page timeout from 1 to 300 seconds; screenshot default is `300`. HTTP deadline is 30 seconds longer. |
| `geo_code`, `proxy_country` | `"US"`, `None` | Geolocation country code and optional `proxyCountry` |
| `browser_rendering` | `None` | Force, disable, or automatically select rendering. Not exposed by `get_screenshot`, which always sends `browserRendering=true`. |
| `super` | `False` | Enable real device routing |
| `use_proxy`, `proxy` | `True`, `None` | Allow a proxy or supply `username:password@host:port` |
| `home_page` | `False` | Visit the site's root first; sent as `warmStart=true` |
| `wait_for_selector`, `wait_until` | `None`, `None` | Wait for a CSS selector or page lifecycle event; screenshot `wait_until` defaults to `"domcontentloaded"` |
| `block_resources`, `bypass_proxy` | `False`, `False` | Block images, CSS, and fonts, or enable proxy bypass behavior |
| `cookie_jar`, `headers` | `None`, `None` | Cookie configuration string and target request headers (dictionary or JSON string) |
| `max_retries`, `token_cap` | `3`, `None` | Retry count and optional token cap; nonnegative values |
| `stream` | `None` | Request a streamed response, buffered by the SDK |
| `discard_token_secret` | `""` | Value for the `x-discard-token-secret` header |

Options set to `None` are omitted. `super`, `warmStart`, `blockResources`, and `bypassProxy` are sent only when enabled. For screenshot GETs and brand creation, `url`, `maxRetries`, and optional `tokenCap` are query parameters. Other scraping POSTs send these fields in the JSON body.

## Get screenshot

`get_screenshot` sends a GET request with `screenshot=full`, `browserRendering=true`, `waitUntil=domcontentloaded`, `timeout=300`, and `maxRetries=3` by default. It omits HTML and Markdown flags. Pass `full_page=False` for `screenshot=true`. Image responses are returned as bytes; the API may also return JSON data.

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

```bash
curl --request GET \
  --url 'https://api.mrscraper.com' \
  --url-query "token=${MRSCRAPER_API_TOKEN}" \
  --url-query 'browserRendering=true' \
  --url-query 'waitUntil=domcontentloaded' \
  --url-query 'timeout=300' \
  --url-query 'geoCode=us' \
  --url-query 'screenshot=full' \
  --url-query 'super=true' \
  --url-query 'proxyCountry=us' \
  --url-query 'tokenCap=30' \
  --url-query 'maxRetries=3' \
  --url-query 'url=https://www.scrapethissite.com' \
  --header "x-api-token: ${MRSCRAPER_API_TOKEN}" \
  --output screenshot.png
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

`scraper_json` sends `agent="general"`, default prompt `"Extract all data as complete as possible."`, and query parameter `html=true`. It omits Markdown and screenshot flags. `scraper_multiple_page` sends `agent="listing"`, default prompt `"Extract all entry data as complete as possible."`, and `maxPages=3`; it omits all output flags.

```bash
curl --request POST \
  --url 'https://api.mrscraper.com' \
  --url-query "token=${MRSCRAPER_API_TOKEN}" \
  --url-query 'geoCode=us' \
  --url-query 'html=true' \
  --url-query 'super=true' \
  --url-query 'proxyCountry=us' \
  --header "x-api-token: ${MRSCRAPER_API_TOKEN}" \
  --header 'Content-Type: application/json' \
  --data '{"url":"https://mrscraper.com/pricing","prompt":"Extract all data as complete as possible.","agent":"general","maxRetries":3}'
```

```bash
curl --request POST \
  --url 'https://api.mrscraper.com' \
  --url-query "token=${MRSCRAPER_API_TOKEN}" \
  --url-query 'geoCode=us' \
  --url-query 'super=true' \
  --url-query 'proxyCountry=us' \
  --header "x-api-token: ${MRSCRAPER_API_TOKEN}" \
  --header 'Content-Type: application/json' \
  --data '{"url":"https://books.toscrape.com","prompt":"Extract all entry data as complete as possible.","agent":"listing","maxPages":3,"maxRetries":3}'
```

## Sitemap discovery

`scraper_sitemap` sends `agent="map"` with defaults `max_depth=2`, `max_pages=3`, and `limit=1000`. It omits HTML, Markdown, and screenshot flags. Optional `include_patterns` and `exclude_patterns` strings map to `includePatterns` and `excludePatterns` in the JSON body. Pattern strings, including regex backslashes, are passed through unchanged; omit them to send no pattern fields.

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

```bash
curl --request POST \
  --url 'https://api.mrscraper.com' \
  --url-query "token=${MRSCRAPER_API_TOKEN}" \
  --url-query 'geoCode=us' \
  --url-query 'proxyCountry=us' \
  --header "x-api-token: ${MRSCRAPER_API_TOKEN}" \
  --header 'Content-Type: application/json' \
  --data '{"url":"https://docs.mrscraper.com","agent":"map","maxDepth":2,"maxPages":3,"limit":1000,"maxRetries":3,"includePatterns":"/docs/.*|/reference/.*","excludePatterns":"\\.(png|jpg)$"}'
```

## Brand scraping

`scrape_brand` sends a POST with `action=brand-scraping`, `bundle`, and `url` in the query; the JSON body contains `url`. `bundle` accepts `"clean"` (default), `"full"`, or `"none"`. Use the job ID from the response with `get_brand` to read the job later or download an output.

```python
job = await client.scrape_brand("https://www.brooksrunning.com", bundle="clean")
print(job["data"])  # Read the returned job ID.

brand = await client.get_brand("YOUR_JOB_ID")
bundle = await client.get_brand("YOUR_JOB_ID", output="bundle")
from pathlib import Path
Path("brand.zip").write_bytes(bundle["data"])
```

`get_brand` calls `GET /neo/brand?id=...` and has a 600-second HTTP timeout by default. Omit `output` for job data or select `"html"`, `"bundle"`, `"screenshot"`, or `"screenshot_full"`. JSON becomes Python values, HTML becomes text, and ZIP or image downloads remain bytes in `data`.

```bash
curl --request POST \
  --url 'https://api.mrscraper.com/' \
  --url-query 'action=brand-scraping' \
  --url-query 'bundle=clean' \
  --url-query 'url=https://www.brooksrunning.com' \
  --header "x-api-token: ${MRSCRAPER_API_TOKEN}" \
  --header 'Content-Type: application/json' \
  --data '{"url":"https://www.brooksrunning.com"}'

# Read the brand again later.
curl --url 'https://api.mrscraper.com/neo/brand' \
  --url-query 'id=YOUR_JOB_ID' \
  --header "x-api-token: ${MRSCRAPER_API_TOKEN}"

# Download an output: html | bundle | screenshot | screenshot_full.
curl --url 'https://api.mrscraper.com/neo/brand' \
  --url-query 'id=YOUR_JOB_ID' \
  --url-query 'output=bundle' \
  --header "x-api-token: ${MRSCRAPER_API_TOKEN}" \
  --output brand.zip
```

## Web search

Web Search retrieves Google search results from a text query or a Google search URL. Use it to discover relevant pages, find URLs to scrape, or collect search results for analysis. Results can be requested as structured JSON or HTML, with options for region, language, results page, and JavaScript rendering.

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

`web_search` sends a `POST` request to `https://sync.scraper.mrscraper.com/api/google/serp/v2/sync`. The first argument accepts query text or a full Google search URL; for a URL, the client extracts `q`, `gl`, `hl`, and `start`. Explicit options override values from the URL. The return value has `status_code`, `data`, and `headers` keys. `raw=True` is the default and requests HTML; set `raw=False` to use `format`.

Full cURL reference with every JSON payload field supported by `web_search`:

```bash
curl --request POST \
  --url 'https://sync.scraper.mrscraper.com/api/google/serp/v2/sync' \
  --header 'Content-Type: application/json' \
  --header 'accept: application/json' \
  --header "Authorization: Bearer ${MRSCRAPER_API_TOKEN}" \
  --header "x-api-token: ${MRSCRAPER_API_TOKEN}" \
  --max-time 600 \
  --data '{
    "query": "python web scraping",
    "region": "us",
    "language": "en",
    "page": 1,
    "format": "json",
    "renderJs": false
  }'
```

The SDK's `url` argument becomes `query`, and `render_js` becomes `renderJs`. For a Google URL, `q`, `gl`, `hl`, and `start` become `query`, `region`, `language`, and a one-based `page`; explicit options override the URL values. `raw` is an SDK option, so it is not sent in the JSON body. With the SDK default `raw=True`, the body uses `"format":"html"` instead. `timeout` controls the HTTP client deadline; the cURL example uses `--max-time 600`.

| Option | Default | Description |
|--------|---------|-------------|
| `url` | required | Search query or Google search URL |
| `raw` | `True` | Request HTML when true, regardless of `format` |
| `format` | `"json"` | `"json"` or `"html"` when `raw=False` |
| `region`, `language` | `None`, `None` | Country and language |
| `page` | `None` | One based results page |
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

`account()` sends `GET https://api.app.mrscraper.com/api/v1/subscription-accounts`
using the client's token in Bearer and `x-api-token` headers. The timeout
defaults to 30 seconds and must be positive. The response has `status_code`,
`data`, and `headers` keys. `data` contains `subscription_status`, `enterprise`,
`token_usage`, `token_limit`, `token_remaining`, `usage_percent`, `rate_limit`,
`rate_ttl`, `auto_renew`, `ends_at`, and `user` (`name`, `email`, `verified`).
Remaining tokens are clamped to zero when usage exceeds the limit. API keys,
billing identifiers, and sensitive response headers are excluded.

Complete cURL request for `account(timeout=30)`. This endpoint has no query parameters or JSON payload; `timeout` controls the HTTP client deadline and is represented here by `--max-time 30`.

```bash
curl --request GET \
  --url 'https://api.app.mrscraper.com/api/v1/subscription-accounts' \
  --header 'Content-Type: application/json' \
  --header 'accept: application/json' \
  --header "Authorization: Bearer ${MRSCRAPER_API_TOKEN}" \
  --header "x-api-token: ${MRSCRAPER_API_TOKEN}" \
  --max-time 30
```

cURL returns the original account payload. Field renaming, quota calculations, and sensitive-field filtering are performed by `account()` in the SDK.

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

Version 0.7.0 is configured in `pyproject.toml` and `src/mrscraper/__init__.py`. Publishing is manual. From the repository root, validate and build the release:

```bash
python -m pip install build twine pytest pytest-asyncio respx
python -m pip install -e .
python -m pytest -m "not integration" -q
python -m build --outdir dist/manual-0.7.0
python -m twine check dist/manual-0.7.0/mrscraper_sdk-0.7.0-py3-none-any.whl dist/manual-0.7.0/mrscraper_sdk-0.7.0.tar.gz
```

Upload those two artifacts when ready to publish:

```bash
python -m twine upload --username __token__ dist/manual-0.7.0/mrscraper_sdk-0.7.0-py3-none-any.whl dist/manual-0.7.0/mrscraper_sdk-0.7.0.tar.gz
```

Twine prompts for your PyPI API token as the password. The upload command explicitly selects only version 0.7.0's wheel and source distribution. Choose a new version and update both version fields and artifact names for the next release.

## Errors

`MrScraperError` is the base exception. `AuthenticationError` indicates a missing or invalid token, `APIError` carries an HTTP `status_code`, and `NetworkError` indicates a connection or timeout failure.

## Compliance & Legal Risk

Scraping login-protected pages can carry legal and compliance risks. Check the target site's terms and applicable law before automating access.

## License

MIT © MrScraper
