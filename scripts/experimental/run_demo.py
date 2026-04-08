#!/usr/bin/env python3
"""Minimal demo: fetch political market trades (90 days). Shows row/col count and sample.
Do NOT use status=settled when filtering by series_ticker - the API returns 0 markets."""
import sys
import time
from datetime import datetime, timezone, timedelta

import requests

BASE = "https://api.elections.kalshi.com/trade-api/v2"

def get(url, params=None):
    params = params or {}
    time.sleep(0.4)
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

# 1) Political series (no status filter - status=settled returns 0 markets here)
print("Fetching Politics series...", flush=True)
data = get(f"{BASE}/series", {"category": "Politics"})
series = data.get("series", [])
tickers = [s["ticker"] for s in series if s.get("ticker")]
print(f"  {len(tickers)} Politics series.", flush=True)
if not tickers:
    print("No series"); sys.exit(1)

# 2) Markets: API returns 0 when multiple series_ticker; request one series at a time
print("Fetching markets (one series at a time)...", flush=True)
markets = []
for t in tickers[:20]:  # first 20 series for demo
    data = get(f"{BASE}/markets", {"series_ticker": t, "limit": 500})
    markets.extend(data.get("markets", []))
mtickers = [m["ticker"] for m in markets if m.get("ticker")]
print(f"  {len(mtickers)} political market tickers.", flush=True)
if not mtickers:
    print("No markets."); sys.exit(1)
mtickers = mtickers[:5]

# 3) Trades for political tickers (paginate one ticker to get a real sample)
end_ts = int(datetime.now(timezone.utc).timestamp())
start_ts = end_ts - 90 * 86400  # 90 days

trades = []
for ticker in mtickers:
    print(f"Fetching trades for {ticker}...", flush=True)
    cursor = None
    while True:
        params = {"ticker": ticker, "min_ts": start_ts, "max_ts": end_ts, "limit": 1000}
        if cursor:
            params["cursor"] = cursor
        data = get(f"{BASE}/markets/trades", params)
        page = data.get("trades", [])
        trades.extend(page)
        cursor = data.get("cursor")
        if not cursor or len(page) < 1000:
            break
    if trades:
        break
if not trades:
    print("No trades in 90 days for first 5 political markets (they may be inactive).", flush=True)
    sys.exit(1)

# 4) Filter value >= 1000, add value_usd
def value_usd(t):
    c = int(t.get("count", 0))
    side = (t.get("taker_side") or "").lower()
    p = float(t.get("yes_price_dollars" if side == "yes" else "no_price_dollars") or "0")
    return c * p

# Filter by min value (use 1 for demo so we get some rows; use 1000 for "over 1K" slice)
MIN_VAL = 1  # set to 1000 for real "over $1K" filter
filtered = []
for t in trades:
    v = value_usd(t)
    if v >= MIN_VAL:
        t = dict(t)
        t["value_usd"] = round(v, 2)
        filtered.append(t)

cols = ["trade_id", "ticker", "price", "count", "count_fp", "yes_price", "no_price", "yes_price_dollars", "no_price_dollars", "taker_side", "created_time", "value_usd"]
print("\n--- Rows and columns (political markets, 90 days) ---")
print(f"Rows: {len(filtered)} (total trades fetched: {len(trades)})")
print(f"Columns: {len(cols)}")
print("\n--- Column names ---")
print(cols)
if filtered:
    print("\n--- Sample rows (first 2) ---")
    for i, t in enumerate(filtered[:2]):
        print(f"  Row {i+1}:", {k: t.get(k) for k in cols})
    # Write sample CSV
    import csv
    out_path = "political_sample.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for t in filtered:
            w.writerow({k: t.get(k, "") for k in cols})
    print(f"\nWrote {len(filtered)} rows to {out_path}")
else:
    print("\n(No trades in this narrow sample; try more tickers or longer window.)")
