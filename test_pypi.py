"""Run one MrScraper method at a time against the real API.

Examples:
    export MRSCRAPER_API_TOKEN="your-token"
    python test_pypi.py --fetch-html
    python test_pypi.py --get-account
    python test_pypi.py --create-ai --target detail --local
    python test_pypi.py --create-ai --target listing --local
    python test_pypi.py --rerun-ai --target detail --scraper-id YOUR_ID --local

By default this imports the installed (PyPI) package. Add --local to import
this repository's src/ version instead. Each run makes exactly one API call.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx


# This file is a manual CLI runner, not a pytest test module.
__test__ = False


DETAIL_URL = "https://www.ebay.com/itm/266727555514"
LISTING_URL = (
    "https://www.ebay.com/sch/i.html?"
    "_nkw=shoes&_sacat=0&_from=R40&_trksid=p2332490.m570.l1313"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run exactly one MrScraper method against the live API.",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    actions = parser.add_mutually_exclusive_group(required=True)
    for flag, name in (
        ("fetch-html", "scraper_html"),
        ("google-serp", "web_search"),
        ("create-ai", "create_ai"),
        ("rerun-ai", "rerun_ai"),
        ("bulk-rerun-ai", "bulk_rerun_ai"),
        ("rerun-manual", "rerun_manual"),
        ("bulk-rerun-manual", "bulk_rerun_manual"),
        ("get-results", "get_results"),
        ("get-result", "get_result"),
        ("get-account", "get_account"),
        ("get-analytics", "get_analytics"),
    ):
        actions.add_argument(f"--{flag}", action="store_const", const=name, dest="action")

    parser.add_argument("--local", action="store_true", help="Import ./src instead of installed PyPI package")
    parser.add_argument("--target", choices=("detail", "listing"), default="detail")
    parser.add_argument("--url", help="Override the selected eBay URL")
    parser.add_argument("--urls", nargs="+", help="Bulk rerun URLs (default: selected URL)")
    parser.add_argument("--scraper-id", help="Existing scraper ID for rerun methods")
    parser.add_argument("--result-id", help="Result ID for --get-result")
    parser.add_argument("--agent", choices=("general", "listing", "map"))
    parser.add_argument("--message", help="Instruction for --create-ai")
    parser.add_argument("--mode", choices=("Cheap", "Super"))
    parser.add_argument("--proxy-country")
    parser.add_argument("--home-page", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--bypass-proxy", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--show-modal", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--use-proxy", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--return-cookies", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--render-javascript", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--html", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--markdown", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--max-depth", type=int, default=1)
    parser.add_argument("--max-pages", type=int, default=3)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--wait-for-selector")
    parser.add_argument("--include-patterns", default="")
    parser.add_argument("--exclude-patterns", default="")
    parser.add_argument("--query", default="site:ebay.com shoes")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=5)
    parser.add_argument("--include-html", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--start-date", help="Required for --get-analytics")
    parser.add_argument("--end-date", help="Required for --get-analytics")
    parser.add_argument("--save-dir", type=Path, help="Save complete response as JSON")
    return parser


def target_url(args: argparse.Namespace) -> str:
    return args.url or (DETAIL_URL if args.target == "detail" else LISTING_URL)


def target_agent(args: argparse.Namespace) -> str:
    return args.agent or ("general" if args.target == "detail" else "listing")


async def test_scraper_html(client: Any, args: argparse.Namespace) -> dict[str, Any]:
    return await client.scraper_html(
        target_url(args), home_page=args.home_page,
        proxy_country=args.proxy_country, timeout=args.timeout,
    )


async def test_web_search(client: Any, args: argparse.Namespace) -> dict[str, Any]:
    return await client.web_search(args.query, raw=False)


async def test_create_ai(client: Any, args: argparse.Namespace) -> dict[str, Any]:
    agent = target_agent(args)
    message = args.message or (
        "Extract the item title, price, condition, seller, and shipping details."
        if agent == "general" else
        "Extract product titles, prices, item URLs, and shipping details."
    )
    return await client.create_scraper(
        target_url(args), None if agent == "map" else message,
        agent=agent, mode=args.mode,
        proxy_country=args.proxy_country if agent != "map" else None,
        home_page=args.home_page,
        max_depth=args.max_depth, max_pages=args.max_pages, limit=args.limit,
        include_patterns=args.include_patterns, exclude_patterns=args.exclude_patterns,
    )


async def test_rerun_ai(client: Any, args: argparse.Namespace) -> dict[str, Any]:
    return await client.rerun_scraper(
        args.scraper_id, target_url(args),
        max_depth=args.max_depth, max_pages=args.max_pages, limit=args.limit,
        include_patterns=args.include_patterns, exclude_patterns=args.exclude_patterns,
        proxy_country=args.proxy_country if target_agent(args) != "map" else None,
        max_retries=args.max_retries, timeout=args.timeout,
        home_page=args.home_page, html=args.html, markdown=args.markdown,
        bypass_proxy=args.bypass_proxy, wait_for_selector=args.wait_for_selector,
        render_javascript=args.render_javascript, use_proxy=args.use_proxy,
        return_cookies=args.return_cookies, show_modal=args.show_modal,
    )


async def test_bulk_rerun_ai(client: Any, args: argparse.Namespace) -> dict[str, Any]:
    return await client.bulk_rerun_ai_scraper(args.scraper_id, args.urls or [target_url(args)])


async def test_rerun_manual(client: Any, args: argparse.Namespace) -> dict[str, Any]:
    return await client.rerun_manual_scraper(
        args.scraper_id, target_url(args), proxy_country=args.proxy_country,
        max_retries=args.max_retries, home_page=args.home_page,
        bypass_proxy=args.bypass_proxy, use_proxy=args.use_proxy,
        html=args.html, markdown=args.markdown, timeout=args.timeout,
    )


async def test_bulk_rerun_manual(client: Any, args: argparse.Namespace) -> dict[str, Any]:
    return await client.bulk_rerun_manual_scraper(args.scraper_id, args.urls or [target_url(args)])


async def test_get_results(client: Any, args: argparse.Namespace) -> dict[str, Any]:
    return await client.get_all_results(
        page=args.page, page_size=args.page_size, scraper_id=args.scraper_id,
    )


async def test_get_result(client: Any, args: argparse.Namespace) -> dict[str, Any]:
    return await client.get_result_by_id(args.result_id, include_html=args.include_html)


async def test_get_account(client: Any, args: argparse.Namespace) -> dict[str, Any]:
    return await client.get_subscription_account()


async def test_get_analytics(client: Any, args: argparse.Namespace) -> dict[str, Any]:
    return await client.get_analytic_statuses("ebay.com", args.start_date, args.end_date)


TESTS = {
    "scraper_html": test_scraper_html,
    "web_search": test_web_search,
    "create_ai": test_create_ai,
    "rerun_ai": test_rerun_ai,
    "bulk_rerun_ai": test_bulk_rerun_ai,
    "rerun_manual": test_rerun_manual,
    "bulk_rerun_manual": test_bulk_rerun_manual,
    "get_results": test_get_results,
    "get_result": test_get_result,
    "get_account": test_get_account,
    "get_analytics": test_get_analytics,
}


async def show_request(request: httpx.Request) -> None:
    print(f"\nREQUEST {request.method} {request.url}")
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
    if args.action in {"rerun_ai", "bulk_rerun_ai", "rerun_manual", "bulk_rerun_manual"}:
        if not args.scraper_id:
            parser.error("--scraper-id is required for this test")
    if args.action == "get_result" and not args.result_id:
        parser.error("--result-id is required for this test")
    if args.action == "get_analytics" and (not args.start_date or not args.end_date):
        parser.error("--start-date and --end-date are required for this test")

    token = os.getenv("MRSCRAPER_API_TOKEN") or os.getenv("MRSCRAPER_TOKEN")
    if not token:
        parser.error("set MRSCRAPER_API_TOKEN (or MRSCRAPER_TOKEN) first")

    if args.local:
        sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
    try:
        package = importlib.import_module("mrscraper")
    except ImportError as exc:
        parser.error(f"cannot import mrscraper: {exc}. Install it or use --local")
    print(f"PACKAGE: {package.__file__}")
    print(f"TEST: {args.action}")
    if args.action in {"scraper_html", "create_ai", "rerun_ai", "rerun_manual"}:
        print(f"TARGET: {target_url(args)} | home_page={args.home_page}")

    async with httpx.AsyncClient(event_hooks={"request": [show_request]}) as http_client:
        client = package.MrScraper(token, http_client=http_client)
        try:
            result = await TESTS[args.action](client, args)
        except Exception:
            print(f"\nFAILED: {args.action}", file=sys.stderr)
            traceback.print_exc()
            return 1

    print(f"\nPASSED: {args.action} (HTTP {result['status_code']})")
    data = result["data"]
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        data = data["data"]
    if isinstance(data, dict):
        for key in ("scraperId", "scraper_id", "resultId", "result_id", "id"):
            if data.get(key):
                print(f"Response {key}: {data[key]}")
    preview = json.dumps(result["data"], indent=2, ensure_ascii=False, default=str)
    print(preview[:3000] + ("\n... (preview truncated)" if len(preview) > 3000 else ""))
    if args.save_dir:
        args.save_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = args.save_dir / f"{args.action}_{stamp}.json"
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        print(f"Full response saved to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
