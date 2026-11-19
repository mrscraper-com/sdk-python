# MrScraper API reference

The public descriptions below use the same standard as the CLI, SDKs, and integrations. Authentication is sent in headers. Account status uses the platform subscription-accounts endpoint; scraping and search use the Scraper API.

## Status

Return the raw account status API response without summarizing, redacting body fields, or adding calculated fields.

This service takes no service parameters. Authentication is configured separately.

The complete account API response body is preserved inside data. If the API wraps account details in data, those details are available at data.data. Sensitive response headers are removed.

## Scrape HTML

Retrieve the raw HTML of a page. Browser rendering is optional.

| Parameter           | HTTP field         | Type                                                            | Default              | Description                                                                                     |
| ------------------- | ------------------ | --------------------------------------------------------------- | -------------------- | ----------------------------------------------------------------------------------------------- |
| `url`               | `url`              | str                                                             | Required             | Absolute HTTP or HTTPS URL of the page to process.                                              |
| `timeout`           | `timeout`          | int                                                             | `300`                | Page load timeout in seconds, from 1 to 300. The HTTP request allows 30 additional seconds.     |
| `geo_code`          | `geoCode`          | str                                                             | `"us"`               | Two-letter country code to load the page from, sent in lowercase.                               |
| `proxy_country`     | `proxyCountry`     | str                                                             | `"us"`               | Two-letter country code of the proxy server, sent in lowercase.                                 |
| `super`             | `super`            | bool                                                            | `False`              | Whether to route the request through real devices.                                              |
| `wait_until`        | `waitUntil`        | str: `domcontentloaded`, `load`, `networkidle0`, `networkidle2` | `"domcontentloaded"` | Navigation completion event to wait for: domcontentloaded, load, networkidle0, or networkidle2. |
| `proxy`             | `proxy`            | str                                                             | `None` (omitted)     | Custom proxy URL used to load the page.                                                         |
| `max_retries`       | `maxRetries`       | int                                                             | `None` (omitted)     | Maximum number of retries, as a nonnegative integer. Omit this parameter for no limit.          |
| `save_result`       | `saveResult`       | bool                                                            | `False`              | Whether to save the result to the dashboard Result tab.                                         |
| `block_resources`   | `blockResources`   | bool                                                            | `False`              | Whether to block images, fonts, and stylesheets while loading the page.                         |
| `wait_for_selector` | `waitForSelector`  | str                                                             | `None` (omitted)     | Wait for the page to contain the specified CSS selector before returning the result.            |
| `return_cookie`     | `returnCookie`     | bool                                                            | `False`              | Whether to include browser session cookies in the response.                                     |
| `browser_rendering` | `browserRendering` | bool                                                            | `False`              | Whether to render the page in a browser before returning the result.                            |
| `warm_start`        | `warmStart`        | bool                                                            | `False`              | Whether to enable warm start for more reliable scraping, at the cost of additional latency.     |

The default response body is HTML text. Additional controls can cause the API to return JSON; the returned structure is preserved.

## Scrape Markdown

Retrieve a page as Markdown. Including HTML also enables browser rendering and returns both outputs as JSON.

| Parameter           | HTTP field         | Type                                                            | Default              | Description                                                                                     |
| ------------------- | ------------------ | --------------------------------------------------------------- | -------------------- | ----------------------------------------------------------------------------------------------- |
| `url`               | `url`              | str                                                             | Required             | Absolute HTTP or HTTPS URL of the page to process.                                              |
| `timeout`           | `timeout`          | int                                                             | `300`                | Page load timeout in seconds, from 1 to 300. The HTTP request allows 30 additional seconds.     |
| `geo_code`          | `geoCode`          | str                                                             | `"us"`               | Two-letter country code to load the page from, sent in lowercase.                               |
| `proxy_country`     | `proxyCountry`     | str                                                             | `"us"`               | Two-letter country code of the proxy server, sent in lowercase.                                 |
| `super`             | `super`            | bool                                                            | `False`              | Whether to route the request through real devices.                                              |
| `wait_until`        | `waitUntil`        | str: `domcontentloaded`, `load`, `networkidle0`, `networkidle2` | `"domcontentloaded"` | Navigation completion event to wait for: domcontentloaded, load, networkidle0, or networkidle2. |
| `proxy`             | `proxy`            | str                                                             | `None` (omitted)     | Custom proxy URL used to load the page.                                                         |
| `max_retries`       | `maxRetries`       | int                                                             | `None` (omitted)     | Maximum number of retries, as a nonnegative integer. Omit this parameter for no limit.          |
| `save_result`       | `saveResult`       | bool                                                            | `False`              | Whether to save the result to the dashboard Result tab.                                         |
| `block_resources`   | `blockResources`   | bool                                                            | `False`              | Whether to block images, fonts, and stylesheets while loading the page.                         |
| `wait_for_selector` | `waitForSelector`  | str                                                             | `None` (omitted)     | Wait for the page to contain the specified CSS selector before returning the result.            |
| `return_cookie`     | `returnCookie`     | bool                                                            | `False`              | Whether to include browser session cookies in the response.                                     |
| `browser_rendering` | `browserRendering` | bool                                                            | `False`              | Whether to render the page in a browser before returning the result.                            |
| `warm_start`        | `warmStart`        | bool                                                            | `False`              | Whether to enable warm start for more reliable scraping, at the cost of additional latency.     |
| `html`              | `html`             | bool                                                            | `False`              | Whether to include the page HTML in the response.                                               |

The default response body is Markdown text. Enabling HTML returns JSON containing both HTML and Markdown.

## Get screenshot

Capture a base64 screenshot of the full page or top viewport. Browser rendering is always enabled.

| Parameter           | HTTP field        | Type                                                            | Default              | Description                                                                                     |
| ------------------- | ----------------- | --------------------------------------------------------------- | -------------------- | ----------------------------------------------------------------------------------------------- |
| `url`               | `url`             | str                                                             | Required             | Absolute HTTP or HTTPS URL of the page to process.                                              |
| `timeout`           | `timeout`         | int                                                             | `300`                | Page load timeout in seconds, from 1 to 300. The HTTP request allows 30 additional seconds.     |
| `geo_code`          | `geoCode`         | str                                                             | `"us"`               | Two-letter country code to load the page from, sent in lowercase.                               |
| `proxy_country`     | `proxyCountry`    | str                                                             | `"us"`               | Two-letter country code of the proxy server, sent in lowercase.                                 |
| `super`             | `super`           | bool                                                            | `False`              | Whether to route the request through real devices.                                              |
| `wait_until`        | `waitUntil`       | str: `domcontentloaded`, `load`, `networkidle0`, `networkidle2` | `"domcontentloaded"` | Navigation completion event to wait for: domcontentloaded, load, networkidle0, or networkidle2. |
| `proxy`             | `proxy`           | str                                                             | `None` (omitted)     | Custom proxy URL used to load the page.                                                         |
| `max_retries`       | `maxRetries`      | int                                                             | `None` (omitted)     | Maximum number of retries, as a nonnegative integer. Omit this parameter for no limit.          |
| `save_result`       | `saveResult`      | bool                                                            | `False`              | Whether to save the result to the dashboard Result tab.                                         |
| `block_resources`   | `blockResources`  | bool                                                            | `False`              | Whether to block images, fonts, and stylesheets while loading the page.                         |
| `wait_for_selector` | `waitForSelector` | str                                                             | `None` (omitted)     | Wait for the page to contain the specified CSS selector before returning the result.            |
| `return_cookie`     | `returnCookie`    | bool                                                            | `False`              | Whether to include browser session cookies in the response.                                     |
| `screenshot`        | `screenshot`      | str: `full`, `top`                                              | `"full"`             | Screenshot area to capture: full for the entire page or top for the top viewport.               |
| `html`              | `html`            | bool                                                            | `True`               | Whether to include the page HTML in the response.                                               |
| `markdown`          | `markdown`        | bool                                                            | `False`              | Whether to include the page Markdown in the response.                                           |

The response body contains a base64 screenshot and requested page outputs. The API can still include HTML when HTML output is disabled.

## Scrape brand

Extract a website's colors, typography, logos, and social links as JSON.

| Parameter | HTTP field | Type | Default  | Description                                        |
| --------- | ---------- | ---- | -------- | -------------------------------------------------- |
| `url`     | `url`      | str  | Required | Absolute HTTP or HTTPS URL of the page to process. |

The response body preserves the API brand result. Brand data is typically available at data.data.brand in the response envelope.

## Scrape JSON

Extract structured JSON from a page using a natural-language prompt. Append Json Schema: and a JSON schema to shape the output.

| Parameter           | HTTP field         | Type                                                            | Default                                       | Description                                                                                             |
| ------------------- | ------------------ | --------------------------------------------------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `url`               | `url`              | str                                                             | Required                                      | Absolute HTTP or HTTPS URL of the page to process.                                                      |
| `timeout`           | `timeout`          | int                                                             | `300`                                         | Page load timeout in seconds, from 1 to 300. The HTTP request allows 30 additional seconds.             |
| `geo_code`          | `geoCode`          | str                                                             | `"us"`                                        | Two-letter country code to load the page from, sent in lowercase.                                       |
| `proxy_country`     | `proxyCountry`     | str                                                             | `"us"`                                        | Two-letter country code of the proxy server, sent in lowercase.                                         |
| `super`             | `super`            | bool                                                            | `False`                                       | Whether to route the request through real devices.                                                      |
| `wait_until`        | `waitUntil`        | str: `domcontentloaded`, `load`, `networkidle0`, `networkidle2` | `"domcontentloaded"`                          | Navigation completion event to wait for: domcontentloaded, load, networkidle0, or networkidle2.         |
| `proxy`             | `proxy`            | str                                                             | `None` (omitted)                              | Custom proxy URL used to load the page.                                                                 |
| `max_retries`       | `maxRetries`       | int                                                             | `None` (omitted)                              | Maximum number of retries, as a nonnegative integer. Omit this parameter for no limit.                  |
| `save_result`       | `saveResult`       | bool                                                            | `False`                                       | Whether to save the result to the dashboard Result tab.                                                 |
| `prompt`            | `prompt`           | str                                                             | `"Extract all data as complete as possible."` | Instructions describing the data to extract. Append Json Schema: and a JSON schema to shape the output. |
| `browser_rendering` | `browserRendering` | bool                                                            | `False`                                       | Whether to render the page in a browser before returning the result.                                    |
| `html`              | `html`             | bool                                                            | `False`                                       | Whether to include the page HTML in the response.                                                       |
| `screenshot`        | `screenshot`       | bool                                                            | `False`                                       | Whether to include a base64 screenshot in the response.                                                 |

The response body contains the extraction result in the API's original structure. Optional HTML and screenshot outputs may add fields.

## Web search

Search the web and return ranked results with titles, URLs, descriptions, and sources.

| Parameter     | HTTP field   | Type | Default  | Description                                                                                       |
| ------------- | ------------ | ---- | -------- | ------------------------------------------------------------------------------------------------- |
| `query`       | `query`      | str  | Required | Search query text, trimmed before sending, containing 1 to 1000 characters.                       |
| `country`     | `country`    | str  | `"us"`   | Two-letter country code to search from, sent in lowercase.                                        |
| `num_results` | `numResults` | int  | `10`     | Number of search results to request, as an integer from 10 to 100. Fewer results may be returned. |

The response body contains success, message, and a data array. Each result includes rank, title, url, description, and source.

## Transport

Status uses a fixed 600-second HTTP deadline. Brand and search use 120 seconds. Page services allow the page timeout plus 30 seconds. JSON extraction switches from GET to POST when the encoded URL exceeds 8,000 characters; url, prompt, and agent move to the JSON body.
