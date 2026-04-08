#!/usr/bin/env python3
"""
Prepare the final enriched dataset for DS4200 project.

Takes the raw 30-day political trades CSV, enriches it with market titles
and event_tickers from the Kalshi API (or existing lookup), then derives
additional features: market_topic, day_of_week, hour_of_day, implied_probability.

Usage:
    python3 scripts/prepare_final_dataset.py
"""

from __future__ import annotations

import csv
import os
import re
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
REQUEST_DELAY_SEC = 0.3
MAX_RETRIES = 5
RETRY_BACKOFF_SEC = 1.5
ET = ZoneInfo("America/New_York")

RAW_CSV = "data/raw/political_2k_30d_all.csv"
EXISTING_LOOKUP = "data/derived/ticker_title_lookup.csv"
OUTPUT_CSV = "data/final/kalshi_political_trades.csv"


def _get(url: str, params: dict) -> requests.Response:
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
    return r  # type: ignore


def load_existing_lookup(path: str) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    if not os.path.exists(path):
        return lookup
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            lookup[row["ticker"]] = {
                "title": row.get("title", ""),
                "event_ticker": row.get("event_ticker", ""),
            }
    return lookup


def fetch_missing_titles(tickers: list[str], existing: dict[str, dict]) -> dict[str, dict]:
    lookup = dict(existing)
    missing = [t for t in tickers if t not in lookup]
    print(f"Need to fetch titles for {len(missing)} tickers (have {len(existing)} cached)")
    for i, ticker in enumerate(missing):
        if (i + 1) % 25 == 0 or i == 0:
            print(f"  Fetching {i+1}/{len(missing)}: {ticker}", file=sys.stderr)
        r = _get(f"{BASE_URL}/markets", {"tickers": ticker, "limit": 1})
        if r.status_code != 200:
            continue
        markets = r.json().get("markets", [])
        if markets:
            m = markets[0]
            lookup[ticker] = {
                "title": m.get("title", ""),
                "event_ticker": m.get("event_ticker", ""),
            }
        else:
            lookup[ticker] = {"title": "", "event_ticker": ""}
    return lookup


TOPIC_RULES: list[tuple[str, re.Pattern]] = [
    ("Government Shutdown", re.compile(
        r"shutdown|shut\s*down|GOVTSHUT|GOVSHUT|GOVTFUND|DHSFUND|DHSFUNDING|"
        r"government.+fund|appropriation|continuing.?resolution", re.I)),
    ("Elections & Nominations", re.compile(
        r"election|nominat|governor|senate\b|house\b|CONTROLH|CONTROLS|GOVPARTY|"
        r"2028RRUN|2026RRUN|DEMPRIMARY|REPPRIMARY|midterm|ballot|vote\b|"
        r"SCOTUS|supreme court|confirm|cabinet|ATTYGENCONFIRM|SECSTATECONFIRM|"
        r"AGCONFIRM|SOSCONFIRM|DOGECONFIRM|TREASCONFIRM|PRESNOMR|PRESNOMD|"
        r"PRESNOMFED|FEDCHAIR|SPECIAL2ND|NJ11|MAYORLA|"
        r"democrat.+nomin|republican.+nomin|presidential.+nomin|"
        r"PRESELECTION", re.I)),
    ("International Affairs", re.compile(
        r"KHAMENEI|PUTIN|ZELENSKY|NETANYAHU|MADURO|KIM\s?JONG|"
        r"TRUDEAU|STARMER|XI\s?JINPING|MODI|ERDOGAN|CARNEY|"
        r"iran|russia|ukraine|israel|china|canada|greenland|"
        r"NATO|FOREIGNLEADER|COUNTRYRECOG|LEADEROUT|LEADERSOUT|"
        r"GREENLAND|GREENTERRITORY|USAEXPAND|VENLEADER|VENEZUELALEADER|"
        r"NEXTUKPM|bangladesh|JULYCHARTER|state.?51|"
        r"territory.+acqui|buy.+greenland|head.?of.?state", re.I)),
    ("Executive Orders & Policy", re.compile(
        r"executive.?order|tariff|DOGE\b|AGENCYELIM|"
        r"FEDRATE|interest.?rate|inflation|FEDCOMBO|"
        r"immigra|deport|border|ICE\b|DEPORTCOUNT|"
        r"TikTok|ban\b|ACAEXT|AMEND22|PARDONS|"
        r"EO\d|EXECORDER|INSURRECTION|SAVEACT|"
        r"SCHEDULE|reschedul|marijuana|GAMBLINGREPEAL|"
        r"MARLAGO|LAGODAYS|TRUMPADMINLEAVE|NOEMOUT|"
        r"LEAVEPOWELL|powell.+leave|CABOUT|"
        r"TRUMPOUT|TRUMPMEET", re.I)),
    ("Media & Mentions", re.compile(
        r"MENTION|SOTU|60MIN|FOXNEWS|CNN|MSNBC|"
        r"TWEET|TRUTH\s?SOCIAL|press.?conf|interview|"
        r"AWARDMENTION|INAUG|LATENIGHT|ATTENDSOTU", re.I)),
    ("Legal & Investigations", re.compile(
        r"ARREST|INDICT|IMPEACH|TRIAL|CONVICT|"
        r"EPSTEIN|CLASSIFIED|SUBPOENA|FBI\b|DOJ\b|"
        r"MNDAYCARE|fraud|investigation|charge", re.I)),
]


def classify_topic(ticker: str, title: str) -> str:
    combined = f"{ticker} {title}"
    for topic_name, pattern in TOPIC_RULES:
        if pattern.search(combined):
            return topic_name
    return "Other Political"


def parse_et_datetime(iso_str: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.astimezone(ET)
    except Exception:
        return None


def main() -> None:
    existing_lookup = load_existing_lookup(EXISTING_LOOKUP)

    tickers_in_data: list[str] = []
    rows: list[dict] = []
    with open(RAW_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        raw_fields = list(reader.fieldnames or [])
        seen_tickers: set[str] = set()
        for row in reader:
            rows.append(row)
            t = row.get("ticker", "")
            if t and t not in seen_tickers:
                seen_tickers.add(t)
                tickers_in_data.append(t)

    print(f"Loaded {len(rows)} rows, {len(tickers_in_data)} unique tickers from {RAW_CSV}")

    lookup = fetch_missing_titles(tickers_in_data, existing_lookup)
    print(f"Title lookup now covers {len(lookup)} tickers")

    out_fields = raw_fields + [
        "title", "event_ticker", "market_topic",
        "day_of_week", "hour_of_day", "implied_probability",
    ]

    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        for row in rows:
            ticker = row.get("ticker", "")
            info = lookup.get(ticker, {})
            title = info.get("title", "")
            event_ticker = info.get("event_ticker", "")

            row["title"] = title
            row["event_ticker"] = event_ticker
            row["market_topic"] = classify_topic(ticker, title)

            dt = parse_et_datetime(row.get("created_time", ""))
            if dt:
                row["day_of_week"] = dt.strftime("%A")
                row["hour_of_day"] = dt.hour
            else:
                row["day_of_week"] = ""
                row["hour_of_day"] = ""

            try:
                row["implied_probability"] = round(float(row.get("yes_price", 0)) / 100, 4)
            except (ValueError, ZeroDivisionError):
                row["implied_probability"] = ""

            writer.writerow(row)

    print(f"Wrote {len(rows)} enriched rows to {OUTPUT_CSV}")

    topic_counts: dict[str, int] = {}
    for row in rows:
        t = row.get("market_topic", "Other Political")
        topic_counts[t] = topic_counts.get(t, 0) + 1
    print("\nMarket topic distribution:")
    for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1]):
        print(f"  {topic}: {count} trades ({count*100/len(rows):.1f}%)")


if __name__ == "__main__":
    main()
