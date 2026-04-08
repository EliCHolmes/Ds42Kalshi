#!/usr/bin/env python3
"""
Visualizations for Kalshi political trades.

Reads the existing trade CSV (default: data/raw/political_500_2k.csv) and produces:
- Daily volume over time (line chart)
- Top N markets by volume (horizontal bar)
- Trade size distribution (histogram)
- Yes vs No volume share (bar)
- Optional timeline of large trades (scatter)

Charts are written into charts/current by default.
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd


def load_trades(csv_path: str) -> pd.DataFrame:
    """Load trades CSV and parse dates."""
    df = pd.read_csv(csv_path)
    df["created_time"] = pd.to_datetime(df["created_time"], utc=True)
    df["date"] = df["created_time"].dt.date
    return df


def ensure_output_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def plot_daily_volume(df: pd.DataFrame, out_dir: str) -> None:
    daily = df.groupby("date")["value_usd"].sum().reset_index()
    plt.figure(figsize=(10, 4))
    plt.plot(daily["date"], daily["value_usd"], marker="o", linewidth=1.5)
    plt.title("Daily political trade volume (USD, value ≥ 500)")
    plt.xlabel("Date")
    plt.ylabel("Total traded value (USD)")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "daily_volume.png"))
    plt.close()


def plot_top_markets(df: pd.DataFrame, out_dir: str, top_n: int = 15) -> None:
    by_ticker = df.groupby("ticker")["value_usd"].sum().sort_values(ascending=False)
    top = by_ticker.head(top_n).iloc[::-1]  # reverse for horizontal bar (smallest at top)
    plt.figure(figsize=(10, 0.5 * len(top) + 1))
    plt.barh(top.index, top.values)
    plt.title(f"Top {len(top)} political markets by traded value (USD, value ≥ 500)")
    plt.xlabel("Total traded value (USD)")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "top_markets_by_volume.png"))
    plt.close()


def plot_trade_size_distribution(df: pd.DataFrame, out_dir: str) -> None:
    plt.figure(figsize=(8, 4))
    # Basic histogram; can be tuned if values are very skewed
    plt.hist(df["value_usd"], bins=40, edgecolor="black")
    plt.title("Distribution of political trade sizes (value ≥ 500 USD)")
    plt.xlabel("Trade value (USD)")
    plt.ylabel("Number of trades")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "trade_size_distribution.png"))
    plt.close()


def plot_yes_no_volume_share(df: pd.DataFrame, out_dir: str) -> None:
    grouped = df.groupby("taker_side")["value_usd"].sum()
    sides = grouped.index.tolist()
    values = grouped.values
    plt.figure(figsize=(6, 4))
    plt.bar(sides, values)
    plt.title("Yes vs No volume (USD, political trades value ≥ 500)")
    plt.xlabel("Taker side")
    plt.ylabel("Total traded value (USD)")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "yes_no_volume_share.png"))
    plt.close()


def plot_timeline_large_trades(df: pd.DataFrame, out_dir: str, min_value: float = 1000.0) -> None:
    large = df[df["value_usd"] >= min_value].copy()
    if large.empty:
        return
    plt.figure(figsize=(10, 4))
    plt.scatter(large["created_time"], large["value_usd"], s=10, alpha=0.7)
    plt.title(f"Timeline of large political trades (value ≥ {min_value:.0f} USD)")
    plt.xlabel("Time")
    plt.ylabel("Trade value (USD)")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "timeline_large_trades.png"))
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize Kalshi political trades from CSV.")
    parser.add_argument(
        "--csv",
        default="data/raw/political_500_2k.csv",
        help="Path to trades CSV (default: data/raw/political_500_2k.csv).",
    )
    parser.add_argument(
        "--out-dir",
        default="charts/current",
        help="Directory to write chart images (default: charts/current).",
    )
    args = parser.parse_args()

    df = load_trades(args.csv)
    ensure_output_dir(args.out_dir)

    print(f"Loaded {len(df)} trades from {args.csv}")
    print("Creating charts in", args.out_dir)

    plot_daily_volume(df, args.out_dir)
    plot_top_markets(df, args.out_dir)
    plot_trade_size_distribution(df, args.out_dir)
    plot_yes_no_volume_share(df, args.out_dir)
    plot_timeline_large_trades(df, args.out_dir)

    print("Done.")


if __name__ == "__main__":
    main()

