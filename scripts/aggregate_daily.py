#!/usr/bin/env python3
"""
Aggregate Kalshi trades to daily-by-ticker statistics.

Input: trades CSV (e.g. data/raw/political_500_2k.csv or an enriched version).
Output: data/derived/daily_by_ticker.csv with columns:
    date,ticker,volume_usd,trade_count
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime


def aggregate_daily(src_path: str, dst_path: str) -> None:
    stats: dict[tuple[str, str], dict[str, float | int]] = {}

    with open(src_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = row.get("ticker")
            created_time = row.get("created_time")
            value_str = row.get("value_usd") or "0"
            if not ticker or not created_time:
                continue
            try:
                dt = datetime.fromisoformat(created_time.replace("Z", "+00:00"))
            except ValueError:
                continue
            date_str = dt.date().isoformat()
            key = (date_str, ticker)
            bucket = stats.setdefault(key, {"volume_usd": 0.0, "trade_count": 0})
            try:
                v = float(value_str)
            except ValueError:
                v = 0.0
            bucket["volume_usd"] = float(bucket["volume_usd"]) + v
            bucket["trade_count"] = int(bucket["trade_count"]) + 1

    with open(dst_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["date", "ticker", "volume_usd", "trade_count"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for (date_str, ticker), vals in sorted(stats.items()):
            writer.writerow(
                {
                    "date": date_str,
                    "ticker": ticker,
                    "volume_usd": f"{vals['volume_usd']:.2f}",
                    "trade_count": int(vals["trade_count"]),
                }
            )


def main() -> None:
    ap = argparse.ArgumentParser(description="Aggregate Kalshi trades CSV to daily-by-ticker stats.")
    ap.add_argument(
        "--csv",
        required=True,
        help="Path to trades CSV.",
    )
    ap.add_argument(
        "--out",
        default="data/derived/daily_by_ticker.csv",
        help="Output CSV path (default: data/derived/daily_by_ticker.csv).",
    )
    args = ap.parse_args()

    aggregate_daily(args.csv, args.out)


if __name__ == "__main__":
    main()

