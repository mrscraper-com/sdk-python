"""Run individual MrScraper SDK methods against the real API.

Set MRSCRAPER_API_TOKEN, then select exactly one method to run. Each response is
printed as a short preview and saved in full under ``manual_results/``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable

# Always exercise the SDK source from this checkout, even if another version is
# installed in the active virtual environment.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mrscraper import MrScraper  # noqa: E402
from mrscraper.exceptions import MrScraperError  # noqa: E402

DEFAULT_URL = "https://books.toscrape.com/"
Handler = Callable[[MrScraper, argparse.Namespace], Awaitable[dict[str, Any]]]


def url_value(value: str) -> str:
    """Validate a URL and unwrap Markdown links copied from rendered docs."""
    markdown_link = re.fullmatch(r"\[[^]]+\]\((https?://[^)]+)\)", value.strip())
    resolved = markdown_link.group(1) if markdown_link else value.strip()
    if not re.match(r"^https?://[^\s]+$", resolved):
        raise argparse.ArgumentTypeError("expected an http:// or https:// URL")
    return resolved


async def fetch_html(client: MrScraper, args: argparse.Namespace) -> dict[str, Any]:
    return await client.fetch_html(
        args.url,
        geo_code=args.geo_code,
        timeout=args.timeout,
        browser_rendering=args.browser_rendering,
        home_page=True,
        html=False,
        markdown=True,
    )


async def fetch_google_serp(
    client: MrScraper, args: argparse.Namespace
) -> dict[str, Any]:
    return await client.fetch_google_serp(
        args.query,
        raw=False,
        region=args.region,
        language=args.language,
        page=args.page,
        format=args.format,
        render_js=args.render_js,
    )


async def create_scraper(client: MrScraper, args: argparse.Namespace) -> dict[str, Any]:
    message = None if args.agent == "map" else args.message
    return await client.create_scraper(
        args.url,
        message,
        agent=args.agent,
        mode=args.mode,
        proxy_country=args.proxy_country if args.agent != "map" else None,
        max_depth=args.max_depth,
        max_pages=args.max_pages,
        limit=args.limit,
    )


async def rerun_scraper(client: MrScraper, args: argparse.Namespace) -> dict[str, Any]:
    if args.agent == "map":
        return await client.rerun_scraper(
            args.scraper_id,
            args.url,
            max_depth=args.max_depth,
            max_pages=args.max_pages,
            limit=args.limit,
        )

    return await client.rerun_scraper(
        args.scraper_id,
        args.url,
        max_pages=args.max_pages,
        proxy_country=args.proxy_country,
        home_page=True,
        markdown=True,
    )


async def bulk_rerun_ai_scraper(
    client: MrScraper, args: argparse.Namespace
) -> dict[str, Any]:
    return await client.bulk_rerun_ai_scraper(args.scraper_id, args.urls)


async def rerun_manual_scraper(
    client: MrScraper, args: argparse.Namespace
) -> dict[str, Any]:
    return await client.rerun_manual_scraper(
        args.scraper_id,
        args.url,
        proxy_country=args.proxy_country,
        use_proxy=True,
        bypass_proxy=True,
        home_page=True,
        markdown=False,
    )


async def bulk_rerun_manual_scraper(
    client: MrScraper, args: argparse.Namespace
) -> dict[str, Any]:
    return await client.bulk_rerun_manual_scraper(args.scraper_id, args.urls)


async def get_all_results(client: MrScraper, args: argparse.Namespace) -> dict[str, Any]:
    return await client.get_all_results(
        page=args.page,
        page_size=args.page_size,
        scraper_id=args.scraper_id,
        status=args.status,
    )


async def get_result_by_id(
    client: MrScraper, args: argparse.Namespace
) -> dict[str, Any]:
    return await client.get_result_by_id(args.result_id, include_html=args.include_html)


async def get_subscription_account(
    client: MrScraper, args: argparse.Namespace
) -> dict[str, Any]:
    del args
    return await client.get_subscription_account()


async def get_analytic_statuses(
    client: MrScraper, args: argparse.Namespace
) -> dict[str, Any]:
    return await client.get_analytic_statuses(
        args.domain,
        args.start_date,
        args.end_date,
        action=args.action,
        api_token_name=args.api_token_name,
    )


def add_scraper_id(parser: argparse.ArgumentParser, *, manual: bool = False) -> None:
    kind = "manual scraper" if manual else "AI scraper"
    parser.add_argument("--scraper-id", required=True, help=f"Existing {kind} ID")


def add_urls(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--urls", nargs="+", required=True, type=url_value, help="One or more target URLs"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manually run one MrScraper SDK method against the real API."
    )
    parser.add_argument(
        "--output-dir",
        default="manual_results",
        help="Directory for full JSON responses (default: manual_results)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    command = subparsers.add_parser("fetch_html", help="Run MrScraper.fetch_html")
    command.add_argument("--url", type=url_value, default=DEFAULT_URL)
    command.add_argument("--geo-code", default="US")
    command.add_argument("--timeout", type=int, default=120)
    command.add_argument(
        "--browser-rendering", action=argparse.BooleanOptionalAction, default=None
    )
    command.add_argument("--home-page", action="store_true")
    command.add_argument("--html", action=argparse.BooleanOptionalAction, default=True)
    command.add_argument("--markdown", action=argparse.BooleanOptionalAction, default=False)
    command.set_defaults(handler=fetch_html)

    command = subparsers.add_parser(
        "fetch_google_serp", help="Run MrScraper.fetch_google_serp"
    )
    command.add_argument("--query", default="web scraping python")
    command.add_argument("--region", default="us")
    command.add_argument("--language", default="en")
    command.add_argument("--page", type=int, default=1)
    command.add_argument("--format", choices=("json", "html"), default="json")
    command.add_argument("--render-js", action="store_true")
    command.set_defaults(handler=fetch_google_serp)

    command = subparsers.add_parser("create_scraper", help="Run MrScraper.create_scraper")
    command.add_argument("--url", type=url_value, default=DEFAULT_URL)
    command.add_argument("--agent", choices=("general", "listing", "map"), default="general")
    command.add_argument("--message", default="Extract book titles and prices")
    command.add_argument("--mode", choices=("Cheap", "Super"))
    command.add_argument("--proxy-country")
    command.add_argument("--max-depth", type=int, default=1)
    command.add_argument("--max-pages", type=int, default=5)
    command.add_argument("--limit", type=int, default=25)
    command.set_defaults(handler=create_scraper)

    command = subparsers.add_parser("rerun_scraper", help="Run MrScraper.rerun_scraper")
    add_scraper_id(command)
    command.add_argument("--url", type=url_value, default=DEFAULT_URL)
    command.add_argument("--agent", choices=("general", "listing", "map"), default="general")
    command.add_argument("--proxy-country")
    command.add_argument("--max-depth", type=int, default=1)
    command.add_argument("--max-pages", type=int, default=5)
    command.add_argument("--limit", type=int, default=25)
    command.set_defaults(handler=rerun_scraper)

    command = subparsers.add_parser(
        "bulk_rerun_ai_scraper", help="Run MrScraper.bulk_rerun_ai_scraper"
    )
    add_scraper_id(command)
    add_urls(command)
    command.set_defaults(handler=bulk_rerun_ai_scraper)

    command = subparsers.add_parser(
        "rerun_manual_scraper", help="Run MrScraper.rerun_manual_scraper"
    )
    add_scraper_id(command, manual=True)
    command.add_argument("--url", type=url_value, default=DEFAULT_URL)
    command.add_argument("--proxy-country")
    command.set_defaults(handler=rerun_manual_scraper)

    command = subparsers.add_parser(
        "bulk_rerun_manual_scraper", help="Run MrScraper.bulk_rerun_manual_scraper"
    )
    add_scraper_id(command, manual=True)
    add_urls(command)
    command.set_defaults(handler=bulk_rerun_manual_scraper)

    command = subparsers.add_parser("get_all_results", help="Run MrScraper.get_all_results")
    command.add_argument("--page", type=int, default=1)
    command.add_argument("--page-size", type=int, default=10)
    command.add_argument("--scraper-id")
    command.add_argument("--status")
    command.set_defaults(handler=get_all_results)

    command = subparsers.add_parser(
        "get_result_by_id", help="Run MrScraper.get_result_by_id"
    )
    command.add_argument("--result-id", required=True)
    command.add_argument(
        "--include-html", action=argparse.BooleanOptionalAction, default=False
    )
    command.set_defaults(handler=get_result_by_id)

    command = subparsers.add_parser(
        "get_subscription_account", help="Run MrScraper.get_subscription_account"
    )
    command.set_defaults(handler=get_subscription_account)

    command = subparsers.add_parser(
        "get_analytic_statuses", help="Run MrScraper.get_analytic_statuses"
    )
    command.add_argument("--domain", required=True)
    command.add_argument("--start-date", required=True, help='Example: "2026-09-01 00:00:00"')
    command.add_argument("--end-date", required=True, help='Example: "2026-09-07 23:59:59"')
    command.add_argument("--action", default="")
    command.add_argument("--api-token-name", default="")
    command.set_defaults(handler=get_analytic_statuses)

    return parser


def save_result(command: str, result: dict[str, Any], output_dir: str) -> Path:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = destination / f"{command}_{timestamp}.json"
    path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return path.resolve()


async def run(args: argparse.Namespace, token: str) -> int:
    client = MrScraper(token=token)
    try:
        result = await args.handler(client, args)
    except (MrScraperError, ValueError) as exc:
        print(f"Request failed: {exc}")
        return 1

    path = save_result(args.command, result, args.output_dir)
    preview = json.dumps(result.get("data"), ensure_ascii=False, default=str)
    if len(preview) > 1000:
        preview = f"{preview[:1000]}..."

    print(f"Status: {result.get('status_code')}")
    print(f"Data preview: {preview}")
    print(f"Full response: {path}")
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    token = os.environ.get("MRSCRAPER_API_TOKEN", "").strip()
    if not token:
        parser.error("Set the MRSCRAPER_API_TOKEN environment variable first")
    return asyncio.run(run(args, token))


if __name__ == "__main__":
    raise SystemExit(main())
