"""Manual live smoke tests. Set MRSCRAPER_API_TOKEN; calls spend API quota.

Results are saved under manual_results/ (git-ignored): one JSON file per call,
decoded screenshots, and summary.json with each call's status, options, and request
line. Credentials travel in headers and never appear in the request line.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from mrscraper import APIError, MrScraper

METHOD_ORDER = (
    "status",
    "scrape-html",
    "scrape-markdown",
    "get-screenshot",
    "scrape-brand",
    "scrape-json",
    "web-search",
)


EXAMPLES = """examples:
  python file.py                                   # all seven services with defaults
  python file.py scrape-html --args '{"screenshot": "top", "max_age": 3600000, "geo_code": "gb"}'
  python file.py scrape-html --args '{"browser_rendering": true, "wait_for_selector": "body"}'
  python file.py scrape-markdown --args '{"browser_rendering": false, "block_resources": true}'
  python file.py get-screenshot --args '{"wait_for_selector": "body", "timeout": 120}'
  python file.py scrape-brand --url https://mrscraper.com/
  python file.py scrape-json --url https://books.toscrape.com/ \\
      --args '{"prompt": "Extract the first 3 books", "html": false, "screenshot": true}'
  python file.py web-search --query "running shoes" --args '{"country": "id", "num_results": 20}'

Options use the SDK's snake_case argument names. wait_for_selector needs a rendered
page, so do not combine it with browser_rendering false.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "method",
        nargs="?",
        default="all",
        type=lambda s: s.replace("_", "-"),
        choices=("all", *METHOD_ORDER),
    )
    parser.add_argument("--url", default="https://example.com")
    parser.add_argument("--query", default="python web scraping")
    parser.add_argument(
        "--args", default="{}", help="JSON keyword options, using Python snake_case names"
    )
    parser.add_argument("--save-dir", type=Path, default=Path("manual_results"))
    return parser


async def run_method(client: MrScraper, args: argparse.Namespace) -> dict[str, Any]:
    options = json.loads(args.args)
    if not isinstance(options, dict):
        raise ValueError("--args must be a JSON object")
    method = getattr(client, args.method.replace("-", "_"))
    if args.method == "status":
        return await method(**options)
    return await method(args.query if args.method == "web-search" else args.url, **options)


async def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    token = os.getenv("MRSCRAPER_API_TOKEN") or os.getenv("MRSCRAPER_API_KEY")
    if not token:
        parser.error("Set MRSCRAPER_API_TOKEN or MRSCRAPER_API_KEY")
    try:
        options = json.loads(args.args)
    except ValueError:
        parser.error("--args must be valid JSON")
    if not isinstance(options, dict):
        parser.error("--args must be a JSON object")
    if args.method == "all" and options:
        parser.error("Select one service when using --args")
    sent: list[str] = []

    async def record(request: httpx.Request) -> None:
        sent.append(f"{request.method} {request.url}")

    out = args.save_dir / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out.mkdir(parents=True, exist_ok=True)
    summary = []
    async with httpx.AsyncClient(event_hooks={"request": [record]}) as http_client:
        client = MrScraper(token, http_client=http_client)
        for method in METHOD_ORDER if args.method == "all" else (args.method,):
            args.method = method
            summary.append(await run_and_save(client, args, options, out, token, sent))
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"{sum(row['passed'] for row in summary)}/{len(summary)} passed")
    return int(any(not row["passed"] for row in summary))


async def run_and_save(
    client: MrScraper,
    args: argparse.Namespace,
    options: dict[str, Any],
    out: Path,
    token: str,
    sent: list[str],
) -> dict[str, Any]:
    """Call one service, save its response and screenshot, and return a summary row."""
    method = args.method
    started = time.monotonic()
    sent.clear()
    row: dict[str, Any] = {"service": method, "options": options}
    try:
        result = await run_method(client, args)
        row["status_code"] = result["status_code"]
        raw = json.dumps(
            result,
            indent=2,
            default=lambda b: {"encoding": "base64", "base64": base64.b64encode(b).decode()},
        )
        (out / f"{method}.json").write_text(raw)
        data = result.get("data")
        if (
            isinstance(data, dict)
            and isinstance(data.get("screenshot"), str)
            and data["screenshot"]
        ):
            image = base64.b64decode(data["screenshot"].split(",")[-1])
            # The API documents PNG, but Scrape HTML has also returned JPEG.
            extension = "jpg" if image[:3] == b"\xff\xd8\xff" else "png"
            (out / f"{method}.{extension}").write_bytes(image)
        if isinstance(data, dict) and data.get("success") is False:
            raise RuntimeError(data.get("message", "Unsuccessful response"))
        print(f"PASS {method} (HTTP {result['status_code']}): {out / (method + '.json')}")
        row["passed"] = True
    except Exception as exc:
        message = str(exc).replace(token, "[REDACTED]")
        print(f"FAIL {method}: {message}")
        row.update(passed=False, error=message)
        if isinstance(exc, APIError):
            row["status_code"] = exc.status_code
    row["request"] = sent[-1] if sent else None
    row["seconds"] = round(time.monotonic() - started, 2)
    return row


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
