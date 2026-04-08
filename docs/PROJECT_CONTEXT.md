# Project Context (Kalshi v1)

## Purpose

This workspace pulls and analyzes **Kalshi political trades** with value filters (e.g., `$500+`, `$2,000+`), then generates visualizations for volume/time/risk analysis.

## Canonical Scripts

- `scripts/fetch_trades.py`
  - Main pipeline.
  - Category filtering via `series -> markets -> ticker set`.
  - Supports:
    - `--global` stream mode (recommended for large pulls).
    - `--resume` checkpointing via `--state-file`.
    - live time-depth progress via `--show-time-depth`.
    - readable ET time column `created_time_et`.
- `scripts/enrich_trades_with_titles.py`
  - Maps market `ticker -> title` and writes lookup.
- `scripts/aggregate_daily.py`
  - Aggregates trades into `date,ticker,volume_usd,trade_count`.
- `scripts/visualize.py`
  - Base charts from raw pull.
- `scripts/visualize_enriched.py`
  - Charts using title lookup + daily aggregates.

## Data Contracts

### Raw pull CSV (`data/raw/*.csv`)

Columns:
- `trade_id`
- `ticker`
- `price`
- `count`
- `count_fp`
- `yes_price`
- `no_price`
- `yes_price_dollars`
- `no_price_dollars`
- `taker_side`
- `created_time` (UTC ISO)
- `created_time_et` (human-readable Eastern time)
- `value_usd` (computed notional)

### Derived CSVs (`data/derived/*.csv`)

- `ticker_title_lookup.csv`:
  - `ticker,event_ticker,title`
- `daily_by_ticker.csv`:
  - `date,ticker,volume_usd,trade_count`

## Operational Notes

- `--days N` limits eligible API window.
- `--max-rows` returns most recent matching rows and can compress date span.
- For full window coverage, run without `--max-rows`.
- If interrupted, rerun with same:
  - `--state-file ...`
  - output path
  - `--resume`

## Known API Quirks

- `GET /markets` with multiple `series_ticker` values can return empty; pipeline queries one series ticker per request.
- Network/DNS errors may happen on long runs; retry logic + checkpoints are enabled in v1 scripts.
