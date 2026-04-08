# Runbook

## 1) Long Pull (political, 30d, $2k+, resumable)

```bash
cd /Users/eliholmes/kalshi
python3 scripts/fetch_trades.py \
  --category Politics \
  --min-value 2000 \
  --days 30 \
  --global \
  --out data/raw/political_2k_30d_all.csv \
  --show-time-depth \
  --progress-every-pages 25 \
  --state-file state/fetch_2k_30d.state.json \
  --save-state-every-pages 25 \
  --resume \
  2>&1 | tee logs/fetch_2k_30d_live.log
```

## 2) Check Progress

```bash
tail -f logs/fetch_2k_30d_live.log
```

Progress line example:
- `Page 21400, total matching so far: 1400, ... depth ~9.10d (30.3%)`

## 3) Resume After Crash

Rerun the exact same command in section 1.

Requirements for resume:
- Same `--state-file`
- Same `--out`
- `--resume` enabled

## 4) Enrich + Aggregate

```bash
python3 scripts/enrich_trades_with_titles.py \
  --csv data/raw/political_500_2k.csv \
  --lookup-out data/derived/ticker_title_lookup.csv \
  --enriched-out data/derived/political_500_2k_with_titles.csv

python3 scripts/aggregate_daily.py \
  --csv data/raw/political_500_2k.csv \
  --out data/derived/daily_by_ticker.csv
```

## 5) Generate Visuals

```bash
python3 scripts/visualize.py \
  --csv data/raw/political_500_2k.csv \
  --out-dir charts/current

python3 scripts/visualize_enriched.py \
  --daily data/derived/daily_by_ticker.csv \
  --lookup data/derived/ticker_title_lookup.csv \
  --out-dir charts/enriched
```
