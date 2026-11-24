# MrScraper API reference

The public descriptions below use the same standard as the CLI, SDKs, and integrations. Authentication is sent in headers. Account status uses the platform subscription-accounts endpoint; scraping and search use the Scraper API.

Response examples show selected keys and types observed in live API responses. Values are placeholders; page content, base64 images, and arrays are abbreviated. Actual responses may contain additional fields.

## Status

Return the raw account status API response without summarizing, redacting body fields, or adding calculated fields.

This service takes no service parameters. Authentication is configured separately.

The API body contains message and data. Account details remain nested in data, including subscriptionItem and scraperAllowance. The response envelope therefore exposes account details at data.data. Sensitive response headers are removed.

**Success response**

```json
{
  "status_code": 200,
  "data": {
    "message": "Example response",
    "data": {
      "id": "ACCOUNT_ID",
      "tokenLimit": 100000,
      "tokenUsage": 2500,
      "stripeStatus": "active",
      "user": {
        "name": "Example user",
        "email": "user@example.com",
        "isVerified": true
      },
      "subscriptionItem": {
        "name": "Example plan",
        "tokenLimit": 100000
      },
      "scraperAllowance": {
        "remaining": 97500,
        "plans": [
          {
            "remaining": 97500
          }
        ]
      }
    }
  },
  "headers": {
    "content-type": "application/json; charset=utf-8"
  }
}
```

## Scrape HTML

Retrieve the raw HTML of a page. Browser rendering is optional.

| Parameter           | HTTP field         | Type           | Default          | Description                                                                                                                                                                                                                                                                                           |
| ------------------- | ------------------ | -------------- | ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `url`               | `url`              | str            | Required         | Absolute HTTP or HTTPS URL of the page to process.                                                                                                                                                                                                                                                    |
| `browser_rendering` | `browserRendering` | bool           | `None` (omitted) | Whether to load the page in a browser: true always does and false never does. Omit it to load the page without a browser first and switch to a browser automatically if the request is blocked.                                                                                                       |
| `timeout`           | `timeout`          | int            | `300`            | Maximum seconds to wait for the scrape, from 1 to 330. The HTTP request allows 30 additional seconds.                                                                                                                                                                                                 |
| `warm_start`        | `warmStart`        | bool           | `False`          | Whether to open the site's home page first to warm the session before loading the target URL.                                                                                                                                                                                                         |
| `block_resources`   | `blockResources`   | bool           | `False`          | Whether to block images, fonts, and stylesheets while loading the page.                                                                                                                                                                                                                               |
| `wait_for_selector` | `waitForSelector`  | str            | `None` (omitted) | CSS selector or text to wait for on the page before returning the result, up to 500 characters.                                                                                                                                                                                                       |
| `action`            | `action`           | str            | `None` (omitted) | Scraper action that routes the request or simply flags it, useful for separating analytics per domain.                                                                                                                                                                                                |
| `geo_code`          | `geoCode`          | str            | `None` (omitted) | Two-letter country code to load the page from, sent in lowercase.                                                                                                                                                                                                                                     |
| `max_age`           | `maxAge`           | int            | `0`              | Return a cached result of the same request when it is newer than the selected age. A cached result costs the same tokens as the original scrape.                                                                                                                                                      |
| `max_retries`       | `maxRetries`       | int            | `None` (omitted) | Maximum number of retries, as a nonnegative integer. Omit this parameter for no limit.                                                                                                                                                                                                                |
| `screenshot`        | `screenshot`       | `False` or str | `False`          | Screenshot to capture with the HTML: false for none, full for the entire page, top for the first viewport, or a WIDTHxHEIGHT viewport from 100 to 3840 pixels with an optional -ZOOM percent from 25 to 300, such as 1280x800 or 1920x1080-75. Setting a screenshot also sends browserRendering=true. |

The response body is HTML text. With a screenshot, the API returns JSON containing html and a base64 screenshot.

**Default HTML text**

```json
{
  "status_code": 200,
  "data": "<html><body>Example page content...</body></html>",
  "headers": {
    "content-type": "text/html; charset=utf-8"
  }
}
```

**With a screenshot**

```json
{
  "status_code": 200,
  "data": {
    "html": "<html>...</html>",
    "screenshot": "BASE64_IMAGE_DATA"
  },
  "headers": {
    "content-type": "application/json; charset=utf-8"
  }
}
```

## Scrape Markdown

Retrieve a page as clean Markdown. Browser rendering is optional.

| Parameter           | HTTP field         | Type | Default          | Description                                                                                                                                                                                     |
| ------------------- | ------------------ | ---- | ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `url`               | `url`              | str  | Required         | Absolute HTTP or HTTPS URL of the page to process.                                                                                                                                              |
| `browser_rendering` | `browserRendering` | bool | `None` (omitted) | Whether to load the page in a browser: true always does and false never does. Omit it to load the page without a browser first and switch to a browser automatically if the request is blocked. |
| `timeout`           | `timeout`          | int  | `300`            | Maximum seconds to wait for the scrape, from 1 to 330. The HTTP request allows 30 additional seconds.                                                                                           |
| `warm_start`        | `warmStart`        | bool | `False`          | Whether to open the site's home page first to warm the session before loading the target URL.                                                                                                   |
| `block_resources`   | `blockResources`   | bool | `False`          | Whether to block images, fonts, and stylesheets while loading the page.                                                                                                                         |
| `wait_for_selector` | `waitForSelector`  | str  | `None` (omitted) | CSS selector or text to wait for on the page before returning the result, up to 500 characters.                                                                                                 |
| `action`            | `action`           | str  | `None` (omitted) | Scraper action that routes the request or simply flags it, useful for separating analytics per domain.                                                                                          |
| `geo_code`          | `geoCode`          | str  | `None` (omitted) | Two-letter country code to load the page from, sent in lowercase.                                                                                                                               |
| `max_age`           | `maxAge`           | int  | `0`              | Return a cached result of the same request when it is newer than the selected age. A cached result costs the same tokens as the original scrape.                                                |
| `max_retries`       | `maxRetries`       | int  | `None` (omitted) | Maximum number of retries, as a nonnegative integer. Omit this parameter for no limit.                                                                                                          |

The response body is Markdown text.

**Default Markdown text**

```json
{
  "status_code": 200,
  "data": "# Example page\n\nExample Markdown content...",
  "headers": {
    "content-type": "text/markdown; charset=utf-8"
  }
}
```

## Get screenshot

Capture a base64 PNG screenshot of the full page. Browser rendering is always enabled.

| Parameter           | HTTP field        | Type | Default          | Description                                                                                                                                      |
| ------------------- | ----------------- | ---- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `url`               | `url`             | str  | Required         | Absolute HTTP or HTTPS URL of the page to process.                                                                                               |
| `timeout`           | `timeout`         | int  | `300`            | Maximum seconds to wait for the scrape, from 1 to 330. The HTTP request allows 30 additional seconds.                                            |
| `wait_for_selector` | `waitForSelector` | str  | `None` (omitted) | CSS selector or text to wait for on the page before returning the result, up to 500 characters.                                                  |
| `geo_code`          | `geoCode`         | str  | `None` (omitted) | Two-letter country code to load the page from, sent in lowercase.                                                                                |
| `max_age`           | `maxAge`          | int  | `0`              | Return a cached result of the same request when it is newer than the selected age. A cached result costs the same tokens as the original scrape. |
| `max_retries`       | `maxRetries`      | int  | `None` (omitted) | Maximum number of retries, as a nonnegative integer. Omit this parameter for no limit.                                                           |

The response body is JSON containing a base64 PNG screenshot of the full page and the page HTML, which the API includes even though html=false is sent.

**Success response**

```json
{
  "status_code": 200,
  "data": {
    "html": "<html>...</html>",
    "screenshot": "BASE64_PNG_DATA"
  },
  "headers": {
    "content-type": "application/json; charset=utf-8"
  }
}
```

## Scrape brand

Extract a website's colors, typography, logos, and social links as JSON.

| Parameter | HTTP field | Type | Default  | Description                                        |
| --------- | ---------- | ---- | -------- | -------------------------------------------------- |
| `url`     | `url`      | str  | Required | Absolute HTTP or HTTPS URL of the page to process. |

The API body contains message and a data object with job_id, status, url, final_url, brand, and error. Brand details are available at data.data.brand in the response envelope.

**Success response**

```json
{
  "status_code": 200,
  "data": {
    "data": {
      "job_id": "JOB_ID",
      "status": "succeeded",
      "url": "https://example.com",
      "final_url": "https://example.com",
      "brand": {
        "name": "Example brand",
        "colors": {
          "background": "#ffffff",
          "text": "#222222"
        },
        "typography": {
          "body": {
            "font_family": "Example font"
          }
        }
      },
      "error": null,
      "bundle_url": null
    },
    "message": "Example response"
  },
  "headers": {
    "content-type": "application/json"
  }
}
```

## Scrape JSON

Extract structured JSON from a page using a natural-language prompt. Append Json Schema: and a JSON schema to shape the output.

| Parameter           | HTTP field         | Type | Default                                       | Description                                                                                                                                                                                     |
| ------------------- | ------------------ | ---- | --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `url`               | `url`              | str  | Required                                      | Absolute HTTP or HTTPS URL of the page to process.                                                                                                                                              |
| `prompt`            | `prompt`           | str  | `"Extract all data as complete as possible."` | Instructions describing the data to extract. Append Json Schema: and a JSON schema to shape the output.                                                                                         |
| `html`              | `html`             | bool | `True`                                        | Whether to include the page HTML in the response.                                                                                                                                               |
| `browser_rendering` | `browserRendering` | bool | `None` (omitted)                              | Whether to load the page in a browser: true always does and false never does. Omit it to load the page without a browser first and switch to a browser automatically if the request is blocked. |
| `timeout`           | `timeout`          | int  | `300`                                         | Maximum seconds to wait for the scrape, from 1 to 330. The HTTP request allows 30 additional seconds.                                                                                           |
| `warm_start`        | `warmStart`        | bool | `False`                                       | Whether to open the site's home page first to warm the session before loading the target URL.                                                                                                   |
| `block_resources`   | `blockResources`   | bool | `False`                                       | Whether to block images, fonts, and stylesheets while loading the page.                                                                                                                         |
| `wait_for_selector` | `waitForSelector`  | str  | `None` (omitted)                              | CSS selector or text to wait for on the page before returning the result, up to 500 characters.                                                                                                 |
| `geo_code`          | `geoCode`          | str  | `None` (omitted)                              | Two-letter country code to load the page from, sent in lowercase.                                                                                                                               |
| `max_age`           | `maxAge`           | int  | `0`                                           | Return a cached result of the same request when it is newer than the selected age. A cached result costs the same tokens as the original scrape.                                                |
| `max_retries`       | `maxRetries`       | int  | `None` (omitted)                              | Maximum number of retries, as a nonnegative integer. Omit this parameter for no limit.                                                                                                          |
| `screenshot`        | `screenshot`       | bool | `False`                                       | Whether to include a base64 screenshot in the response.                                                                                                                                         |

Extraction results are in the API body's data field and follow the requested schema. Response metadata includes thread_id, token_usage, status, error, runtime, and cookies. html contains the page HTML unless disabled; markdown and screenshot can be empty strings.

**Success response**

```json
{
  "status_code": 200,
  "data": {
    "success": true,
    "data": [
      {
        "title": "Example item",
        "price": "10.00"
      }
    ],
    "thread_id": "THREAD_ID",
    "token_usage": 1,
    "html": "<html>...</html>",
    "markdown": "",
    "screenshot": "",
    "status": "Results ready",
    "error": "",
    "runtime": 1.23,
    "cookies": []
  },
  "headers": {
    "content-type": "application/json"
  }
}
```

## Web search

Search the web and return ranked results with titles, URLs, descriptions, and sources.

| Parameter     | HTTP field   | Type | Default          | Description                                                                                       |
| ------------- | ------------ | ---- | ---------------- | ------------------------------------------------------------------------------------------------- |
| `query`       | `query`      | str  | Required         | Search query text, trimmed before sending, containing 1 to 1000 characters.                       |
| `country`     | `country`    | str  | `None` (omitted) | Two-letter country code to search from, sent in lowercase.                                        |
| `num_results` | `numResults` | int  | `10`             | Number of search results to request, as an integer from 10 to 100. Fewer results may be returned. |

The API body contains success, message, a data array, and tokenUsage. Each result includes rank, title, url, description, and source.

**Success response**

```json
{
  "status_code": 200,
  "data": {
    "success": true,
    "message": "Example response",
    "data": [
      {
        "rank": 1,
        "title": "Example result",
        "url": "https://example.com",
        "description": "Example result description.",
        "source": "example.com"
      }
    ],
    "tokenUsage": 1
  },
  "headers": {
    "content-type": "application/json; charset=utf-8"
  }
}
```

## Transport

Status uses a fixed 600-second HTTP deadline. Brand and search use 120 seconds. Page services allow the page timeout plus 30 seconds. JSON extraction switches from GET to POST when the encoded URL exceeds 8,000 characters; url, prompt, and agent move to the JSON body.
