"""Manual live smoke tests. Set MRSCRAPER_API_TOKEN; calls spend API quota."""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from mrscraper import MrScraper

METHOD_ORDER = (
    "status",
    "scrape-html",
    "scrape-markdown",
    "get-screenshot",
    "scrape-brand",
    "scrape-json",
    "web-search",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
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
    client = MrScraper(token)
    out = args.save_dir / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out.mkdir(parents=True, exist_ok=True)
    summary = []
    for method in METHOD_ORDER if args.method == "all" else (args.method,):
        args.method = method
        try:
            result = await run_method(client, args)
            raw = json.dumps(
                result,
                indent=2,
                default=lambda b: {"encoding": "base64", "base64": base64.b64encode(b).decode()},
            )
            (out / f"{method}.json").write_text(raw)
            data = result.get("data")
            if isinstance(data, dict) and isinstance(data.get("screenshot"), str):
                (out / f"{method}.png").write_bytes(
                    base64.b64decode(data["screenshot"].split(",")[-1])
                )
            if isinstance(data, dict) and data.get("success") is False:
                raise RuntimeError(data.get("message", "Unsuccessful response"))
            print(f"PASS {method} (HTTP {result['status_code']}): {out / (method + '.json')}")
            summary.append({"service": method, "passed": True})
        except Exception as exc:
            print(f"FAIL {method}: {str(exc).replace(token, '[REDACTED]')}")
            summary.append({"service": method, "passed": False})
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"{sum(row['passed'] for row in summary)}/{len(summary)} passed")
    return int(any(not row["passed"] for row in summary))


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
