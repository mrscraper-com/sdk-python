"""Smoke test the two MrScraper services from this checkout.

Set MRSCRAPER_API_TOKEN, then run one service per invocation::

    python file.py fetch-content --url https://example.com --super
    python file.py google-serp --query "site:example.com"

Each invocation makes one live API request. Use --help for all options.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from mrscraper import MrScraper, MrScraperError  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("method", choices=("fetch-content", "google-serp"))
    parser.add_argument("--url", default="https://www.ebay.com/itm/266727555514")
    parser.add_argument("--query", default="site:ebay.com shoes")
    parser.add_argument("--timeout", type=int, help="Request timeout in seconds")
    parser.add_argument("--save-dir", type=Path, help="Save the full response as JSON")

    # Fetch content options.
    parser.add_argument("--geo-code", default="US")
    parser.add_argument("--proxy-country")
    parser.add_argument("--home-page", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--super",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="enable real-device routing for fetch-content (default: off)",
    )
    parser.add_argument("--screenshot", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--browser-rendering", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--html", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--markdown", action=argparse.BooleanOptionalAction, default=False)

    # Google SERP options.
    parser.add_argument("--region")
    parser.add_argument("--language")
    parser.add_argument("--page", type=int)
    parser.add_argument("--format", choices=("json", "html"), default="json")
    parser.add_argument("--raw", action="store_true", help="Request raw HTML instead of JSON")
    parser.add_argument("--render-js", action="store_true")
    return parser


async def run_method(client: MrScraper, args: argparse.Namespace) -> dict[str, Any]:
    timeout = {"timeout": args.timeout} if args.timeout is not None else {}
    if args.method == "fetch-content":
        return await client.fetch_content(
            args.url,
            html=args.html,
            markdown=args.markdown,
            geo_code=args.geo_code,
            proxy_country=args.proxy_country,
            home_page=args.home_page,
            super=args.super,
            screenshot=args.screenshot,
            browser_rendering=args.browser_rendering,
            **timeout,
        )
    return await client.google_serp(
        args.query,
        raw=args.raw,
        region=args.region,
        language=args.language,
        page=args.page,
        format=args.format,
        render_js=args.render_js,
        **timeout,
    )


async def show_request(request: httpx.Request) -> None:
    safe_url = request.url
    if "token" in safe_url.params:
        safe_url = safe_url.copy_set_param("token", "[REDACTED]")
    print(f"\nREQUEST {request.method} {safe_url}")
    if request.headers.get("content-type", "").startswith("application/json"):
        try:
            body = json.loads(request.content)
        except (ValueError, TypeError):
            return
        if isinstance(body, dict):
            for key in ("token", "proxy", "cookieJar", "cookie_jar"):
                if body.get(key):
                    body[key] = "***"
        print(json.dumps(body, indent=2, ensure_ascii=False))


async def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    token = os.getenv("MRSCRAPER_API_TOKEN") or os.getenv("MRSCRAPER_TOKEN")
    if not token:
        parser.error("set MRSCRAPER_API_TOKEN (or MRSCRAPER_TOKEN) first")

    async with httpx.AsyncClient(event_hooks={"request": [show_request]}) as http_client:
        client = MrScraper(token, http_client=http_client)
        try:
            result = await run_method(client, args)
        except (MrScraperError, ValueError) as exc:
            print(f"\nERROR: {exc}", file=sys.stderr)
            return 1

    print(f"\nHTTP {result['status_code']}")
    preview = json.dumps(result["data"], indent=2, ensure_ascii=False, default=str)
    print(preview[:3000] + ("\n... (preview truncated)" if len(preview) > 3000 else ""))
    if args.save_dir:
        args.save_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = args.save_dir / f"{args.method}_{stamp}.json"
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        print(f"Full response saved to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
