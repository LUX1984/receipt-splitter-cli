#!/usr/bin/env python3
"""Open-source CLI: Parse any restaurant/grocery receipt photo into structured JSON & split totals via Gemini Vision."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

from gemini_client import GeminiReceiptParser


async def run_cli(args: argparse.Namespace) -> None:
    api_key = args.api_key or os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Set GEMINI_API_KEY or pass --api-key")
    img = Path(args.image).resolve()
    if not img.exists():
        raise SystemExit(f"Image not found: {img}")

    mime = "image/png" if img.suffix.lower() == ".png" else "image/jpeg"
    parser = GeminiReceiptParser(api_key, proxy_url=os.getenv("GEMINI_PROXY_URL", ""))
    parsed = await parser.parse_receipt(img.read_bytes(), mime_type=mime)
    print(json.dumps(parsed, ensure_ascii=False, indent=2))


def main() -> None:
    p = argparse.ArgumentParser(description="Extract itemized bill JSON from receipt photos using Gemini Vision")
    p.add_argument("image", help="Path to receipt photo (.jpg / .png)")
    p.add_argument("--api-key", help="Gemini API key")
    asyncio.run(run_cli(p.parse_args()))


if __name__ == "__main__":
    main()
