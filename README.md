# Kalshi Political Trades Workspace

Clean v1 workspace for pulling, enriching, and visualizing Kalshi political trade data.

## Folder Layout

```text
kalshi/
  scripts/            # executable Python scripts
  scripts/experimental/
  data/raw/           # raw pulls from API
  data/derived/       # enriched/aggregated outputs
  charts/current/     # charts from visualize.py
  charts/enriched/    # charts from visualize_enriched.py
  logs/               # long-running pull logs
  state/              # checkpoint/resume state files
  docs/               # context + runbook for future AI sessions
  requirements.txt
```

## Quick Start

```bash
cd /Users/eliholmes/kalshi
pip install -r requirements.txt
```

## Core Workflow

1) Pull trades (political only, with resume/progress):

```bash
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
  --resume
```

2) Enrich with titles:

```bash
python3 scripts/enrich_trades_with_titles.py \
  --csv data/raw/political_500_2k.csv \
  --lookup-out data/derived/ticker_title_lookup.csv \
  --enriched-out data/derived/political_500_2k_with_titles.csv
```

3) Aggregate daily:

```bash
python3 scripts/aggregate_daily.py \
  --csv data/raw/political_500_2k.csv \
  --out data/derived/daily_by_ticker.csv
```

4) Generate charts:

```bash
python3 scripts/visualize.py \
  --csv data/raw/political_500_2k.csv \
  --out-dir charts/current

python3 scripts/visualize_enriched.py \
  --daily data/derived/daily_by_ticker.csv \
  --lookup data/derived/ticker_title_lookup.csv \
  --out-dir charts/enriched
```

## Notes

- `created_time` is raw UTC ISO from API; `created_time_et` is human-readable US Eastern.
- For long pulls, monitor logs in `logs/` and checkpoint state in `state/`.
- For complete window coverage, **omit** `--max-rows`.

See `docs/PROJECT_CONTEXT.md` and `docs/RUNBOOK.md` for full context.
