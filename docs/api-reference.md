# MrScraper REST API reference

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

## Authentication and examples

Use `Authorization: Bearer YOUR_TOKEN` and/or `x-api-token: YOUR_TOKEN`. Never place credentials in a URL.

```bash
curl --get 'https://api.mrscraper.com' \
  --header "x-api-token: $MRSCRAPER_API_TOKEN" \
  --data-urlencode 'url=https://books.toscrape.com/' \
  --data-urlencode 'html=true' \
  --data-urlencode 'markdown=false' \
  --data-urlencode 'screenshot=false'

curl --get 'https://api.mrscraper.com' \
  --header "x-api-token: $MRSCRAPER_API_TOKEN" \
  --data-urlencode 'action=websearch' \
  --data-urlencode 'query=web scraping' \
  --data-urlencode 'country=us' \
  --data-urlencode 'numResults=10'
```

The Python SDK wraps responses as `{ "status_code": 200, "data": ..., "headers": ... }`. It preserves upstream JSON, text, and binary bodies; account returns a summary that excludes credentials and billing identifiers. Screenshot JSON contains a base64 image. Search JSON contains `success`, `message`, and `data`, with ranked `rank`, `title`, `url`, `description`, and `source` fields.

Missing/invalid credentials raise `AuthenticationError`; non-success HTTP responses raise `APIError` with `status_code`; HTTP transport failures raise `NetworkError`. Input validation raises `ValueError` before sending a request.

The SDK sends only the documented fields for each service. Legacy job, sitemap, retry-token budget, and bundle-download endpoints are outside the public seven-service API. See the [README](../README.md) for migration and manual testing.
