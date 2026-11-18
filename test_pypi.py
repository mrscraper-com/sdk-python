"""Compatibility entry point for the seven-service manual runner (not a pytest module)."""

import asyncio

from file import main

__test__ = False
if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
