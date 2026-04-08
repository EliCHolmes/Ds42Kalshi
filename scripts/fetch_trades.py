#!/usr/bin/env python3
"""
Fetch Kalshi historical trades filtered by category (e.g. political), date range, and min value.

Uses ticker-based category filtering: resolve category → series → market tickers,
then request trades only for those tickers (Option A in the plan).

Usage:
  python fetch_trades.py --category Politics --min-value 1000 --days 365 --out political_trades_1k.csv
  python fetch_trades.py --list-categories   # discover category values from API
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

import requests

ET = ZoneInfo("America/New_York")

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
REQUEST_DELAY_SEC = 0.25  # faster polling while still avoiding 429s
MAX_RETRIES = 8
RETRY_BACKOFF_SEC = 1.5


def _get(url: str, params: dict) -> requests.Response:
    """GET with delay and retry on 429."""
    time.sleep(REQUEST_DELAY_SEC)
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, params=params, timeout=30)
            if r.status_code == 429 and attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF_SEC * (attempt + 1))
                continue
            return r
        except requests.exceptions.RequestException:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF_SEC * (attempt + 1))
                continue
            raise
    return r


def get_series(category: str | None = None) -> list[dict]:
    """Fetch all series, optionally filtered by category."""
    url = f"{BASE_URL}/series"
    params = {}
    if category:
        params["category"] = category
    out = []
    while True:
        r = _get(url, params)
        r.raise_for_status()
        data = r.json()
        out.extend(data.get("series", []))
        if not data.get("cursor"):
            break
        params["cursor"] = data["cursor"]
    return out


def get_markets_for_series(series_tickers: list[str]) -> list[dict]:
    """Fetch markets for given series tickers. API returns 0 if multiple series_ticker; use one per request."""
    all_markets = []
    for i, ticker in enumerate(series_tickers):
        if (i + 1) % 100 == 0 or i == 0:
            print(f"  Markets: series {i + 1}/{len(series_tickers)}", file=sys.stderr)
        url = f"{BASE_URL}/markets"
        params = {"series_ticker": ticker, "limit": 1000}
        while True:
            r = _get(url, params)
            r.raise_for_status()
            data = r.json()
            page = data.get("markets", [])
            all_markets.extend(page)
            cursor = data.get("cursor")
            if not cursor or len(page) < 1000:
                break
            params["cursor"] = cursor
    return all_markets


def get_trades(
    ticker: str,
    min_ts: int,
    max_ts: int,
    limit: int = 1000,
) -> list[dict]:
    """Fetch all trades for one market ticker in [min_ts, max_ts], paginated."""
    url = f"{BASE_URL}/markets/trades"
    params = {"ticker": ticker, "min_ts": min_ts, "max_ts": max_ts, "limit": limit}
    out = []
    while True:
        r = _get(url, params)
        r.raise_for_status()
        data = r.json()
        page = data.get("trades", [])
        out.extend(page)
        cursor = data.get("cursor")
        if not cursor or len(page) < limit:
            break
        params["cursor"] = cursor
    return out


def get_trades_global_page(
    min_ts: int,
    max_ts: int,
    cursor: str | None = None,
    limit: int = 1000,
) -> dict:
    """Fetch one page of trades (all markets) in [min_ts, max_ts]. Returns {trades, cursor}."""
    url = f"{BASE_URL}/markets/trades"
    params = {"min_ts": min_ts, "max_ts": max_ts, "limit": limit}
    if cursor:
        params["cursor"] = cursor
    r = _get(url, params)
    r.raise_for_status()
    return r.json()


def trade_value_usd(t: dict) -> float:
    """Notional value in USD: count * price_dollars for the taker side."""
    count = int(t.get("count", 0))
    side = (t.get("taker_side") or "").lower()
    if side == "yes":
        price_str = t.get("yes_price_dollars") or "0"
    else:
        price_str = t.get("no_price_dollars") or "0"
    price = float(price_str)
    return count * price


def format_time_et(iso_str: str) -> str:
    """Convert ISO 8601 UTC string to readable US Eastern time."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.astimezone(ET).strftime("%Y-%m-%d %I:%M %p ET")
    except Exception:
        return iso_str


def parse_iso_utc(iso_str: str) -> datetime | None:
    """Parse ISO 8601 UTC string into datetime, handling variable microseconds."""
    if not iso_str:
        return None
    s = iso_str.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        # Some API timestamps have 5-digit fractional seconds; normalize to 6.
        if "." in s:
            head, tail = s.split(".", 1)
            tz_pos = tail.find("+")
            if tz_pos == -1:
                return None
            frac = tail[:tz_pos]
            tz = tail[tz_pos:]
            frac = (frac + "000000")[:6]
            try:
                return datetime.fromisoformat(f"{head}.{frac}{tz}")
            except ValueError:
                return None
    return None


def save_state(path: str, state: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f)


def load_state(path: str) -> dict | None:
    if not path or not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_existing_trade_ids(path: str) -> set[str]:
    ids: set[str] = set()
    if not path or not os.path.exists(path) or os.path.getsize(path) == 0:
        return ids
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tid = row.get("trade_id")
            if tid:
                ids.add(tid)
    return ids


def run(
    category: str,
    min_value_usd: float,
    days_back: int,
    output_path: str | None,
    list_categories_only: bool = False,
    limit_tickers: int | None = None,
    limit_series: int | None = None,
    use_global: bool = False,
    max_rows: int | None = None,
    show_time_depth: bool = False,
    progress_every_pages: int = 100,
    state_file: str | None = None,
    resume: bool = False,
    save_state_every_pages: int = 50,
) -> None:
    if list_categories_only:
        series_list = get_series()
        categories = sorted({s.get("category") or "" for s in series_list if s.get("category")})
        print("Categories found in API (use one with --category):")
        for c in categories:
            print(f"  {c}")
        return

    # 1) Series for category
    series_list = get_series(category=category)
    if not series_list:
        print(f"No series found for category={category!r}. Try --list-categories.", file=sys.stderr)
        sys.exit(1)
    series_tickers = [s["ticker"] for s in series_list if s.get("ticker")]
    if limit_series is not None:
        series_tickers = series_tickers[:limit_series]
        print(f"Limited to first {limit_series} series (--limit-series).", file=sys.stderr)
    else:
        print(f"Using all {len(series_tickers)} series for category (no --limit-series; no cherry-picking).", file=sys.stderr)

    # 2) Markets for those series (one series_ticker per request; API returns 0 for multiple)
    markets = get_markets_for_series(series_tickers)
    market_tickers = [m["ticker"] for m in markets if m.get("ticker")]
    if not market_tickers:
        print("No markets found for that category.", file=sys.stderr)
        sys.exit(1)
    political_tickers = set(market_tickers)  # full set for --global filtering
    if limit_tickers is not None:
        market_tickers = market_tickers[: limit_tickers]
        print(f"Limited to first {limit_tickers} tickers (--limit-tickers).", file=sys.stderr)

    # 3) Time range (last N days)
    end_ts = int(datetime.now(timezone.utc).timestamp())
    start_ts = int((datetime.now(timezone.utc) - timedelta(days=days_back)).timestamp())

    cols = [
        "trade_id", "ticker", "price", "count", "count_fp",
        "yes_price", "no_price", "yes_price_dollars", "no_price_dollars",
        "taker_side", "created_time", "created_time_et", "value_usd",
    ]

    # Stream rows directly to CSV in global mode when no max_rows cap.
    stream_global = use_global and max_rows is None and output_path is not None
    filtered_trades = []
    rows_written = 0
    seen_trade_ids: set[str] = set()
    stream_file = None
    stream_writer = None

    if stream_global:
        file_exists = os.path.exists(output_path) and os.path.getsize(output_path) > 0
        if resume and file_exists:
            seen_trade_ids = load_existing_trade_ids(output_path)
            rows_written = len(seen_trade_ids)
            print(f"Resume mode: loaded {rows_written} existing rows from {output_path}", file=sys.stderr)
        stream_file = open(output_path, "a" if file_exists else "w", newline="", encoding="utf-8")
        stream_writer = csv.DictWriter(stream_file, fieldnames=cols, extrasaction="ignore")
        if not file_exists:
            stream_writer.writeheader()

    # 4) Fetch trades: global (paginate all trades, filter by ticker) or per-ticker
    if use_global:
        # Option B: one stream of all trades in range; filter by political ticker + value
        print(f"Fetching all trades in range (filtering by {len(political_tickers)} political tickers)...", file=sys.stderr)
        cursor = None
        page_num = 0
        oldest_seen: datetime | None = None
        if resume and state_file:
            st = load_state(state_file)
            if st:
                cursor = st.get("cursor")
                page_num = int(st.get("page_num", 0))
                old = st.get("oldest_seen")
                oldest_seen = parse_iso_utc(old) if old else None
                if stream_global:
                    rows_written = max(rows_written, int(st.get("rows_written", 0)))
                else:
                    print("Resume state found, but non-stream mode requires re-collecting in-memory rows.", file=sys.stderr)
                print(
                    f"Resuming from page {page_num + 1} with cursor {'set' if cursor else 'empty'}"
                    f"{', oldest seen ' + old if old else ''}.",
                    file=sys.stderr,
                )
        while True:
            page_num += 1
            data = get_trades_global_page(start_ts, end_ts, cursor=cursor, limit=1000)
            page = data.get("trades", [])
            if show_time_depth and page:
                # Track oldest trade timestamp seen in the global stream to show time coverage.
                page_times = [parse_iso_utc(t.get("created_time", "")) for t in page]
                page_times = [dt for dt in page_times if dt is not None]
                if page_times:
                    page_oldest = min(page_times)
                    if oldest_seen is None or page_oldest < oldest_seen:
                        oldest_seen = page_oldest
            for t in page:
                if t.get("ticker") not in political_tickers:
                    continue
                v = trade_value_usd(t)
                if v >= min_value_usd:
                    row = dict(t)
                    row["value_usd"] = round(v, 2)
                    row["created_time_et"] = format_time_et(row.get("created_time", ""))
                    if stream_global:
                        tid = row.get("trade_id")
                        if tid and tid in seen_trade_ids:
                            continue
                        stream_writer.writerow({k: row.get(k, "") for k in cols})
                        if tid:
                            seen_trade_ids.add(tid)
                        rows_written += 1
                    else:
                        filtered_trades.append(row)
            if page_num % progress_every_pages == 0 or page_num == 1:
                current_rows = rows_written if stream_global else len(filtered_trades)
                if show_time_depth and oldest_seen is not None:
                    depth_days = (datetime.now(timezone.utc) - oldest_seen).total_seconds() / 86400
                    coverage_days = min(depth_days, float(days_back))
                    coverage_pct = (coverage_days / float(days_back)) * 100.0 if days_back > 0 else 0.0
                    print(
                        f"  Page {page_num}, total matching so far: {current_rows}, "
                        f"oldest seen: {oldest_seen.isoformat()}, depth ~{depth_days:.2f}d "
                        f"({coverage_days:.2f}/{days_back}d = {coverage_pct:.1f}%)",
                        file=sys.stderr,
                    )
                else:
                    print(f"  Page {page_num}, total matching so far: {current_rows}", file=sys.stderr)

            next_cursor = data.get("cursor")
            if state_file and page_num % save_state_every_pages == 0:
                save_state(
                    state_file,
                    {
                        "cursor": next_cursor,
                        "page_num": page_num,
                        "rows_written": rows_written if stream_global else len(filtered_trades),
                        "oldest_seen": oldest_seen.isoformat() if oldest_seen else "",
                        "category": category,
                        "min_value_usd": min_value_usd,
                        "days_back": days_back,
                        "use_global": use_global,
                    },
                )

            if max_rows is not None and len(filtered_trades) >= max_rows:
                break
            cursor = next_cursor
            if not cursor or len(page) < 1000:
                break
    else:
        # Option A: one request per market ticker
        for i, ticker in enumerate(market_tickers):
            if max_rows is not None and len(filtered_trades) >= max_rows:
                break
            if (i + 1) % 50 == 0 or i == 0:
                print(f"Fetching trades for market {i + 1}/{len(market_tickers)}: {ticker}", file=sys.stderr)
            trades = get_trades(ticker, start_ts, end_ts)
            for t in trades:
                v = trade_value_usd(t)
                if v >= min_value_usd:
                    row = dict(t)
                    row["value_usd"] = round(v, 2)
                    row["created_time_et"] = format_time_et(row.get("created_time", ""))
                    filtered_trades.append(row)

    if stream_file is not None:
        stream_file.flush()
        stream_file.close()
        if state_file and os.path.exists(state_file):
            os.remove(state_file)
        if rows_written == 0:
            print("No trades matched filters.", file=sys.stderr)
            return
        print(f"Rows: {rows_written}, Columns: {len(cols)}", file=sys.stderr)
        print(f"Wrote {output_path}", file=sys.stderr)
        return

    # 5) Cap to most recent max_rows (by created_time) if requested
    if max_rows is not None and len(filtered_trades) > max_rows:
        filtered_trades.sort(key=lambda t: t.get("created_time") or "", reverse=True)
        filtered_trades = filtered_trades[:max_rows]
        print(f"Kept most recent {max_rows} trades.", file=sys.stderr)

    # 6) Output
    if not filtered_trades:
        print("No trades matched filters.", file=sys.stderr)
        return

    rows = len(filtered_trades)
    print(f"Rows: {rows}, Columns: {len(cols)}", file=sys.stderr)

    if output_path:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for t in filtered_trades:
                w.writerow({k: t.get(k, "") for k in cols})
        print(f"Wrote {output_path}", file=sys.stderr)
    else:
        w = csv.DictWriter(sys.stdout, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for t in filtered_trades:
            w.writerow({k: t.get(k, "") for k in cols})


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch Kalshi historical trades by category and min value.")
    ap.add_argument("--category", default="Politics", help="Series category (e.g. Politics). Use --list-categories to discover.")
    ap.add_argument("--min-value", type=float, default=1000, help="Minimum trade value in USD (default 1000).")
    ap.add_argument("--days", type=int, default=365, help="Look back this many days (default 365).")
    ap.add_argument("--out", dest="output", default=None, help="Output CSV path (default: stdout).")
    ap.add_argument("--list-categories", action="store_true", help="List category values from API and exit.")
    ap.add_argument("--limit-tickers", type=int, default=None, help="Max market tickers to fetch (for quick tests).")
    ap.add_argument("--limit-series", type=int, default=None, help="Max series to fetch markets for (speeds up --global with category).")
    ap.add_argument("--global", dest="use_global", action="store_true", help="Fetch all trades in range and filter by category (scales to millions of rows).")
    ap.add_argument("--max-rows", type=int, default=None, help="Stop after this many matching trades; output is sorted to most recent (for 'last N' trades).")
    ap.add_argument("--show-time-depth", action="store_true", help="In --global mode, print oldest timestamp reached and approximate days covered.")
    ap.add_argument("--progress-every-pages", type=int, default=100, help="Print progress every N pages in --global mode (default 100).")
    ap.add_argument("--state-file", default="state/fetch_state.json", help="Path to checkpoint state JSON for resume in --global mode.")
    ap.add_argument("--resume", action="store_true", help="Resume from --state-file cursor if available.")
    ap.add_argument("--save-state-every-pages", type=int, default=50, help="Save resume state every N pages in --global mode (default 50).")
    args = ap.parse_args()

    run(
        category=args.category,
        min_value_usd=args.min_value,
        days_back=args.days,
        output_path=args.output,
        list_categories_only=args.list_categories,
        limit_tickers=args.limit_tickers,
        limit_series=args.limit_series,
        use_global=args.use_global,
        max_rows=args.max_rows,
        show_time_depth=args.show_time_depth,
        progress_every_pages=args.progress_every_pages,
        state_file=args.state_file,
        resume=args.resume,
        save_state_every_pages=args.save_state_every_pages,
    )


if __name__ == "__main__":
    main()
