#!/usr/bin/env python3
"""
Enrich a Kalshi trades CSV with human-readable market titles.

For each distinct `ticker` in the input CSV, this script calls the
`GET /markets` endpoint with `tickers=<ticker>` and extracts:
- ticker
- event_ticker
- title

Outputs:
- data/derived/ticker_title_lookup.csv  (ticker,event_ticker,title)
- Optionally, an enriched copy of the trades CSV with a `title` column.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from typing import Dict, List

import requests

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
REQUEST_DELAY_SEC = 0.5
MAX_RETRIES = 3
RETRY_BACKOFF_SEC = 2.0


def _get(url: str, params: dict) -> requests.Response:
    """GET with delay and simple retry on 429."""
    time.sleep(REQUEST_DELAY_SEC)
    for attempt in range(MAX_RETRIES):
        r = requests.get(url, params=params, timeout=30)
        if r.status_code == 429 and attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_BACKOFF_SEC * (attempt + 1))
            continue
        return r
    return r


def read_unique_tickers(csv_path: str) -> List[str]:
    tickers = set()
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            t = row.get("ticker")
            if t:
                tickers.add(t)
    return sorted(tickers)


def fetch_titles_for_tickers(tickers: List[str]) -> Dict[str, dict]:
    """Return mapping ticker -> {ticker,event_ticker,title}."""
    result: Dict[str, dict] = {}
    for i, ticker in enumerate(tickers):
        if (i + 1) % 50 == 0 or i == 0:
            print(f"Fetching metadata for ticker {i + 1}/{len(tickers)}: {ticker}", file=sys.stderr)
        url = f"{BASE_URL}/markets"
        params = {"tickers": ticker, "limit": 1}
        r = _get(url, params)
        r.raise_for_status()
        data = r.json()
        markets = data.get("markets", [])
        if not markets:
            continue
        m = markets[0]
        result[ticker] = {
            "ticker": m.get("ticker", ticker),
            "event_ticker": m.get("event_ticker") or "",
            "title": m.get("title") or "",
        }
    return result


def write_lookup(lookup_path: str, mapping: Dict[str, dict]) -> None:
    with open(lookup_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["ticker", "event_ticker", "title"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for t in sorted(mapping.keys()):
            writer.writerow(mapping[t])


def write_enriched_csv(src_path: str, dst_path: str, mapping: Dict[str, dict]) -> None:
    with open(src_path, newline="", encoding="utf-8") as src, open(
        dst_path, "w", newline="", encoding="utf-8"
    ) as dst:
        reader = csv.DictReader(src)
        fieldnames = list(reader.fieldnames or [])
        if "title" not in fieldnames:
            fieldnames.append("title")
        writer = csv.DictWriter(dst, fieldnames=fieldnames)
        writer.writeheader()
        for row in reader:
            t = row.get("ticker")
            info = mapping.get(t or "", {})
            row["title"] = info.get("title", "")
            writer.writerow(row)


def main() -> None:
    ap = argparse.ArgumentParser(description="Enrich Kalshi trades CSV with market titles.")
    ap.add_argument(
        "--csv",
        required=True,
        help="Path to trades CSV (e.g. data/raw/political_500_2k.csv).",
    )
    ap.add_argument(
        "--lookup-out",
        default="data/derived/ticker_title_lookup.csv",
        help="Path for ticker->title lookup CSV (default: data/derived/ticker_title_lookup.csv).",
    )
    ap.add_argument(
        "--enriched-out",
        default=None,
        help="Optional path for enriched trades CSV with an added 'title' column.",
    )
    args = ap.parse_args()

    tickers = read_unique_tickers(args.csv)
    print(f"Found {len(tickers)} unique tickers in {args.csv}", file=sys.stderr)
    mapping = fetch_titles_for_tickers(tickers)
    print(f"Got titles for {len(mapping)} tickers", file=sys.stderr)

    write_lookup(args.lookup_out, mapping)
    print(f"Wrote lookup to {args.lookup_out}", file=sys.stderr)

    if args.enriched_out:
        write_enriched_csv(args.csv, args.enriched_out, mapping)
        print(f"Wrote enriched CSV to {args.enriched_out}", file=sys.stderr)


if __name__ == "__main__":
    main()

