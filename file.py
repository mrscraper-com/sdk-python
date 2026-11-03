"""Smoke test the public MrScraper methods: scraper_api, web_search, and account.

Set your MrScraper API token, then run all public methods or pick one::

    export MRSCRAPER_API_TOKEN="YOUR_MRSCRAPER_API_TOKEN"
    python file.py
    python file.py all --super
    python file.py account --timeout 30
    python file.py scraper-api --markdown --screenshot
    python file.py web-search --query "e-menessaptieka.lv linkedin" --country us --num-results 10

Private helpers can still be exercised one at a time, for example
``python file.py scraper-sitemap --include-patterns '/property/.*'``.

The default target is https://www.cireba.com/cayman-islands-real-estate-listings/.
Results are saved under manual_results/<run timestamp>/ with a summary.json.
All mode runs account, scraper-api, and web-search and continues after failures.
Each selected method makes a live API request. Use --help for all options.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any
from urllib.parse import urlparse

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from mrscraper import MrScraper, MrScraperError  # noqa: E402

DEFAULT_URL = "https://www.cireba.com/cayman-islands-real-estate-listings/"
METHOD_ORDER = ("account", "scraper-api", "web-search")
PRIVATE_METHODS = (
    "scraper-html", "scraper-markdown", "get-screenshot",
    "scraper-json", "scraper-multiple-page", "scraper-sitemap",
    "scrape-brand", "get-brand",
)


def normalize_method(value: str) -> str:
    return value.replace("_", "-")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "method",
        nargs="?",
        default="all",
        type=normalize_method,
        choices=("all", *METHOD_ORDER, *PRIVATE_METHODS, "fetch-content"),
        help="Method to test (default: all). Underscores are also accepted.",
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="Target URL (default: CIREBA listings)")
    parser.add_argument("--query", help="Search query (default: site:<target URL hostname>)")
    parser.add_argument("--timeout", type=int, help="Request timeout in seconds")
    parser.add_argument(
        "--save-dir", type=Path, default=Path("manual_results"),
        help="Results directory (default: manual_results); each run gets a timestamped folder",
    )

    # Common scraping options; each method selects its own output format.
    parser.add_argument("--geo-code", default="US")
    parser.add_argument("--proxy-country")
    parser.add_argument("--home-page", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument(
        "--super",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="enable real-device routing for scraping (default: off)",
    )
    parser.add_argument("--browser-rendering", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--token-cap", type=int)
    parser.add_argument("--full-page", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--wait-until", default="domcontentloaded")
    parser.add_argument("--bundle", choices=("clean", "full", "none"), default="clean")
    parser.add_argument("--job-id", help="Brand job ID for get-brand")
    parser.add_argument("--output", choices=("html", "bundle", "screenshot", "screenshot_full"))
    parser.add_argument("--prompt", help="Extraction instructions for JSON or multiple pages")
    parser.add_argument("--max-pages", type=int, default=3)
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--include-patterns", help="URL pattern string for sitemap discovery")
    parser.add_argument("--exclude-patterns", help="URL pattern string to exclude from sitemap discovery")

    # scraper-api output flags.
    parser.add_argument("--html", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--markdown", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--screenshot", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--block-resources", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--wait-for-selector", help="CSS selector to wait for before returning")

    # Web search options.
    parser.add_argument("--country", help="Country code for web-search results, e.g. us")
    parser.add_argument("--num-results", type=int, default=10, help="Results from 10 to 100")
    return parser


async def run_method(client: MrScraper, args: argparse.Namespace) -> dict[str, Any]:
    timeout = {"timeout": args.timeout} if args.timeout is not None else {}
    if args.method == "account":
        return await client.account(**timeout)
    if args.method == "get-brand":
        if not args.job_id:
            raise ValueError("--job-id is required for get-brand")
        return await client._get_brand(args.job_id, output=args.output, **timeout)
    common = {
        "geo_code": args.geo_code,
        "proxy_country": args.proxy_country,
        "home_page": args.home_page,
        "super": args.super,
        "browser_rendering": args.browser_rendering,
        "max_retries": args.max_retries,
        "token_cap": args.token_cap,
        **timeout,
    }
    if args.method == "scraper-api":
        return await client.scraper_api(
            args.url, html=args.html, markdown=args.markdown, screenshot=args.screenshot,
            block_resources=args.block_resources, wait_for_selector=args.wait_for_selector,
            **common,
        )
    if args.method in {"fetch-content", "scraper-html"}:
        return await client._scraper_html(args.url, **common)
    if args.method == "scraper-markdown":
        return await client._scraper_markdown(args.url, **common)
    if args.method == "get-screenshot":
        common.pop("browser_rendering")
        return await client._get_screenshot(
            args.url, full_page=args.full_page, wait_until=args.wait_until, **common,
        )
    if args.method == "scrape-brand":
        return await client._scrape_brand(args.url, bundle=args.bundle, **common)
    if args.method in {"scraper-json", "scraper-multiple-page"}:
        prompt = {"prompt": args.prompt} if args.prompt is not None else {}
        if args.method == "scraper-json":
            return await client._scraper_json(args.url, **prompt, **common)
        return await client._scraper_multiple_page(
            args.url, max_pages=args.max_pages, **prompt, **common,
        )
    if args.method == "scraper-sitemap":
        return await client._scraper_sitemap(
            args.url, max_depth=args.max_depth, max_pages=args.max_pages,
            limit=args.limit, include_patterns=args.include_patterns,
            exclude_patterns=args.exclude_patterns, **common,
        )
    if args.method != "web-search":
        raise ValueError(f"Unknown method: {args.method}")
    return await client.web_search(
        args.query or f"site:{urlparse(args.url).hostname or 'cireba.com'}",
        country=args.country,
        num_results=args.num_results,
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


def find_brand_job_id(data: Any) -> str | None:
    """Read a job ID from a brand response, including data/job wrappers."""
    if not isinstance(data, dict):
        return None
    for key in ("jobId", "job_id", "id"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, int) and not isinstance(value, bool):
            return str(value)
    for key in ("data", "job"):
        job_id = find_brand_job_id(data.get(key))
        if job_id is not None:
            return job_id
    return None


def report_result(method: str, result: dict[str, Any], save_dir: Path) -> Path:
    """Preview a response and preserve JSON, text, or binary output on disk."""
    print(f"HTTP {result['status_code']}")
    data = result["data"]
    if isinstance(data, bytes):
        print(f"Binary response: {len(data)} bytes")
    else:
        preview = data if isinstance(data, str) else json.dumps(data, indent=2, ensure_ascii=False)
        print(preview[:3000] + ("\n... (preview truncated)" if len(preview) > 3000 else ""))

    save_dir.mkdir(parents=True, exist_ok=True)
    content_type = result.get("headers", {}).get("content-type", "").split(";", 1)[0].lower()
    if isinstance(data, bytes):
        extension = {
            "application/zip": ".zip", "application/x-zip-compressed": ".zip",
            "image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp",
            "image/svg+xml": ".svg", "application/pdf": ".pdf",
        }.get(content_type, ".bin")
        path = save_dir / f"{method}{extension}"
        path.write_bytes(data)
    elif isinstance(data, str):
        extension = {
            "text/html": ".html", "text/markdown": ".md", "text/plain": ".txt",
        }.get(content_type, ".txt")
        if method in {"scraper-api", "scraper-html", "fetch-content"}:
            extension = ".html"
        elif method == "scraper-markdown":
            extension = ".md"
        path = save_dir / f"{method}{extension}"
        path.write_text(data, encoding="utf-8")
    else:
        path = save_dir / f"{method}.json"
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    if isinstance(data, (str, bytes)):
        metadata = {key: value for key, value in result.items() if key != "data"}
        metadata["data_file"] = path.name
        (save_dir / f"{method}.meta.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8",
        )
    print(f"Saved: {path}")
    return path


async def run_tests(client: MrScraper, args: argparse.Namespace) -> int:
    """Run selected methods sequentially, recording failures without stopping all mode."""
    methods = METHOD_ORDER if args.method == "all" else (args.method,)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%fZ")
    save_dir = args.save_dir / stamp
    save_dir.mkdir(parents=True, exist_ok=True)
    print(f"Target: {args.url}")
    print(f"Testing: {args.method} ({len(methods)} method(s))")
    print(f"Results: {save_dir}")
    rows: list[dict[str, Any]] = []
    brand_job_id = args.job_id

    for index, method in enumerate(methods, 1):
        print(f"\n[{index}/{len(methods)}] {method}", flush=True)
        step_args = argparse.Namespace(**vars(args))
        step_args.method = method
        if method == "get-brand" and args.method == "all":
            if not brand_job_id:
                reason = "No brand job ID available; pass --job-id or inspect the scrape-brand response."
                print(f"SKIP: {reason}")
                rows.append({"method": method, "status": "SKIP", "error": reason})
                continue
            step_args.job_id = brand_job_id
        started = perf_counter()
        try:
            result = await run_method(client, step_args)
            path = report_result(method, result, save_dir)
            rows.append({
                "method": method, "status": "PASS", "status_code": result["status_code"],
                "seconds": round(perf_counter() - started, 2),
                "file": str(path) if path is not None else None,
            })
            if method == "scrape-brand" and not brand_job_id:
                brand_job_id = find_brand_job_id(result["data"])
                if brand_job_id:
                    print(f"Brand job ID: {brand_job_id}")
        except (MrScraperError, ValueError, OSError, AttributeError) as exc:
            print(f"FAIL: {exc}", file=sys.stderr, flush=True)
            rows.append({
                "method": method, "status": "FAIL", "error": str(exc),
                "seconds": round(perf_counter() - started, 2),
            })

    print("\nResults:")
    for row in rows:
        detail = f"HTTP {row['status_code']}" if row["status"] == "PASS" else row["error"]
        print(f"{row['status']:4}  {row['method']:22}  {detail}")
    counts = {status: sum(row["status"] == status for row in rows) for status in ("PASS", "FAIL", "SKIP")}
    print(f"\n{counts['PASS']} passed, {counts['FAIL']} failed, {counts['SKIP']} skipped")
    summary = {
        "url": args.url, "method": args.method, "brand_job_id": brand_job_id,
        "counts": counts, "results": rows,
    }
    summary_path = save_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Summary: {summary_path}")
    return 1 if counts["FAIL"] or counts["SKIP"] else 0


async def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    token = os.getenv("MRSCRAPER_API_TOKEN") or os.getenv("MRSCRAPER_TOKEN")
    if not token or not token.strip():
        parser.error("set MRSCRAPER_API_TOKEN (or MRSCRAPER_TOKEN) first")

    async with httpx.AsyncClient(event_hooks={"request": [show_request]}) as http_client:
        return await run_tests(MrScraper(token, http_client=http_client), args)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
