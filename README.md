# MrScraper Python SDK

![](./mrscraper.jpeg)

An async Python client for [MrScraper](https://mrscraper.com) content fetching and Google SERP. Requires Python 3.9+.

## Install and authenticate

```bash
python -m pip install -e .
export MRSCRAPER_API_TOKEN="YOUR_TOKEN"
```

These commands install the current checkout. After version 0.4.0 is published, install it from PyPI with `python -m pip install --upgrade mrscraper-sdk`. The client reads `MRSCRAPER_API_TOKEN` automatically. You can also pass `token="YOUR_TOKEN"` to `MrScraper`. Pass `http_client=` if you want to reuse your own `httpx.AsyncClient`; otherwise the SDK creates one per request. Both methods are async and must be awaited.

## Fetch content

```python
import asyncio
from mrscraper import MrScraper

async def main():
    client = MrScraper()
    result = await client.fetch_content("https://example.com")
    print(result["data"])

asyncio.run(main())
```

`fetch_content` sends a `POST` request to `https://api.mrscraper.com`. The JSON body contains the target URL, `maxRetries`, and optional `tokenCap`. Page options and the token are query parameters. The return value has `status_code`, `data`, and `headers` keys. The SDK parses JSON responses into Python values and returns other responses as text. Depending on the requested options, `data` may contain HTML, Markdown, a screenshot, or a combination; inspect the returned value before assuming it is an HTML string.

To request HTML, Markdown, and a screenshot together:

```python
import asyncio
from mrscraper import MrScraper

async def main():
    client = MrScraper()
    result = await client.fetch_content(
        "https://example.com",
        html=True,
        markdown=True,
        screenshot=True,
        super=True,
    )
    print(result["data"])

asyncio.run(main())
```

Setting `screenshot=True` also enables browser rendering, even if `browser_rendering=False` is passed.

| Option | Default | Description |
|--------|---------|-------------|
| `url` | required | Target URL |
| `html`, `markdown` | `True`, `False` | Request HTML, Markdown, or both |
| `timeout` | `120` | Page timeout in seconds, from 1 to 300 |
| `geo_code`, `proxy_country` | `"US"`, `None` | Geolocation country code and optional `proxyCountry` field |
| `browser_rendering` | `None` | `True` to force browser rendering, `False` to disable it, or `None` for automatic fallback |
| `screenshot` | `False` | Capture a screenshot; also forces browser rendering |
| `super` | `False` | Enable real device routing |
| `use_proxy`, `proxy` | `True`, `None` | Allow a proxy or supply `username:password@host:port` |
| `home_page` | `False` | Visit the site's root first; sent as `warmStart=true` |
| `wait_for_selector` | `None` | Wait for a CSS selector |
| `block_resources`, `bypass_proxy` | `False`, `False` | Block images, CSS, and fonts, or enable the API's proxy bypass behavior |
| `cookie_jar`, `headers` | `None`, `None` | Cookie configuration string and target request headers (dictionary or JSON string) |
| `max_retries`, `token_cap` | `3`, `None` | Retry controls |
| `stream` | `None` | Request a streamed response, buffered by the SDK |
| `discard_token_secret` | `""` | Value for the `x-discard-token-secret` header |

## Google SERP

```python
import asyncio
from mrscraper import MrScraper

async def main():
    client = MrScraper()
    result = await client.google_serp(
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

`google_serp` sends a `POST` request to `https://sync.scraper.mrscraper.com/api/google/serp/v2/sync`. The first argument accepts query text or a full Google search URL; for a URL, the client extracts `q`, `gl`, `hl`, and `start`. Explicit options override values from the URL. The return value has `status_code`, `data`, and `headers` keys. `raw=True` is the default and requests HTML; set `raw=False` to use `format`.

| Option | Default | Description |
|--------|---------|-------------|
| `url` | required | Search query or Google search URL |
| `raw` | `True` | Request HTML when true, regardless of `format` |
| `format` | `"json"` | `"json"` or `"html"` when `raw=False` |
| `region`, `language` | `None`, `None` | Country and language |
| `page` | `None` | One based results page |
| `render_js` | `False` | Render JavaScript features |
| `timeout` | `600.0` | Request timeout in seconds |

## Smoke test this checkout

`file.py` runs one live request per invocation. Set your token first, then run:

```bash
python file.py fetch-content --url "https://example.com" --super
python file.py google-serp --query "site:example.com" --format json
```

The `fetch-content` command calls `fetch_content()` and enables `screenshot=true` and `warmStart=true` by default. Pass `--super` to enable real device routing; the printed request URL should contain `super=true`. The `google-serp` command calls `google_serp()` and requests JSON by default.

Use `python file.py --help` for the available options. Add `--save-dir manual_results` to save a full JSON response.

## Publishing a release

Publishing is manual. Choose a version that has not been published to PyPI and set it in both `pyproject.toml` and `src/mrscraper/__init__.py`. This checkout is prepared for `0.4.0`. From the repository root, run:

```bash
python -m pip install build twine pytest pytest-asyncio
python -m pip install -e .
python -m pytest -m "not integration" -q
python -m build --outdir dist/manual-0.4.0
ls dist/manual-0.4.0
python -m twine check dist/manual-0.4.0/mrscraper_sdk-0.4.0*
python -m twine upload --username __token__ dist/manual-0.4.0/mrscraper_sdk-0.4.0*
```

Before uploading, confirm that `ls` shows only the intended 0.4.0 files. Twine prompts for a [PyPI API token](https://pypi.org/manage/account/#api-tokens) as the password. Do not upload older files from `dist/`.

## Errors

`MrScraperError` is the base exception. `AuthenticationError` indicates a missing or invalid token, `APIError` carries an HTTP `status_code`, and `NetworkError` indicates a connection or timeout failure.

## Compliance & Legal Risk

Scraping login-protected pages can carry legal and compliance risks. Check the target site's terms and applicable law before automating access.

## License

MIT © MrScraper
