#!/usr/bin/env python3
"""
Visualizations that use enriched Kalshi trade data:

- Volume by event/market title (top N)
- Daily volume by market (top N), using aggregated daily stats

Assumes you have already run:
- enrich_trades_with_titles.py --csv data/raw/political_500_2k.csv --enriched-out data/derived/political_500_2k_with_titles.csv
- aggregate_daily.py --csv data/raw/political_500_2k.csv --out data/derived/daily_by_ticker.csv
"""

from __future__ import annotations

import argparse
import os

import matplotlib.pyplot as plt
import pandas as pd


def ensure_output_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def load_lookup(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def load_daily(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    return df


def merge_titles(daily: pd.DataFrame, lookup: pd.DataFrame) -> pd.DataFrame:
    return daily.merge(lookup[["ticker", "title"]], on="ticker", how="left")


def plot_volume_by_title(daily_with_titles: pd.DataFrame, out_dir: str, top_n: int = 15) -> None:
    by_title = (
        daily_with_titles.groupby("title")["volume_usd"]
        .sum()
        .sort_values(ascending=False)
    )
    by_title = by_title.head(top_n).iloc[::-1]
    plt.figure(figsize=(10, 0.4 * len(by_title) + 1))
    plt.barh(by_title.index, by_title.values)
    plt.title(f"Top {len(by_title)} political markets by volume (USD, value ≥ 500)")
    plt.xlabel("Total traded value (USD)")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "top_markets_by_title.png"))
    plt.close()


def plot_daily_volume_by_market(daily_with_titles: pd.DataFrame, out_dir: str, top_n: int = 5) -> None:
    # Choose top markets by total volume
    totals = (
        daily_with_titles.groupby(["ticker", "title"])["volume_usd"]
        .sum()
        .sort_values(ascending=False)
    )
    top_pairs = totals.head(top_n).index.tolist()
    top = daily_with_titles.set_index(["ticker", "title"]).loc[top_pairs].reset_index()

    plt.figure(figsize=(10, 5))
    for (ticker, title), group in top.groupby(["ticker", "title"]):
        group_sorted = group.sort_values("date")
        plt.plot(group_sorted["date"], group_sorted["volume_usd"], marker="o", label=title or ticker)

    plt.title(f"Daily volume by market (top {top_n} by total volume, value ≥ 500)")
    plt.xlabel("Date")
    plt.ylabel("Daily traded value (USD)")
    plt.xticks(rotation=45, ha="right")
    plt.legend(loc="upper left", fontsize="small")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "daily_volume_by_market.png"))
    plt.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="Visualize enriched Kalshi political trade data.")
    ap.add_argument(
        "--daily",
        default="data/derived/daily_by_ticker.csv",
        help="Daily-by-ticker CSV (from aggregate_daily.py).",
    )
    ap.add_argument(
        "--lookup",
        default="data/derived/ticker_title_lookup.csv",
        help="Ticker-title lookup CSV (from enrich_trades_with_titles.py).",
    )
    ap.add_argument(
        "--out-dir",
        default="charts/enriched",
        help="Directory to write chart images (default: charts/enriched).",
    )
    args = ap.parse_args()

    ensure_output_dir(args.out_dir)
    daily = load_daily(args.daily)
    lookup = load_lookup(args.lookup)

    # Ensure numeric volume
    daily["volume_usd"] = pd.to_numeric(daily["volume_usd"], errors="coerce").fillna(0.0)

    merged = merge_titles(daily, lookup)

    plot_volume_by_title(merged, args.out_dir)
    plot_daily_volume_by_market(merged, args.out_dir)

    print("Enriched visualizations written to", args.out_dir)


if __name__ == "__main__":
    main()

