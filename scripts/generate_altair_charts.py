#!/usr/bin/env python3
"""
Generate all Altair visualizations for the DS4200 Kalshi project.

Reads data/final/kalshi_political_trades.csv and outputs 4 standalone HTML
charts into site/charts/.

Viz 1: Daily Trade Volume Over Time (line + annotations + brush)
Viz 2: Top 12 Markets Yes/No Stacked Bar
Viz 3: Trade Size Distribution by Market Topic
Viz 4: Implied Probability vs Trade Value (scatter)
"""

from __future__ import annotations

import os
import pandas as pd
import altair as alt

DATA_PATH = "data/final/kalshi_political_trades.csv"
OUT_DIR = "site/charts"

CB_PALETTE = ["#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE", "#AA3377", "#BBBBBB"]
YES_NO_COLORS = ["#4477AA", "#EE6677"]

EVENTS = [
    {"date": "2026-01-20", "label": "Inauguration Day"},
    {"date": "2026-02-01", "label": "Gov Funding Deadline"},
    {"date": "2026-02-14", "label": "Shutdown Deadline (Feb 14)"},
]


def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df["created_time"] = pd.to_datetime(df["created_time"], utc=True)
    df["value_usd"] = pd.to_numeric(df["value_usd"], errors="coerce").fillna(0)
    df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0)
    df["implied_probability"] = pd.to_numeric(df["implied_probability"], errors="coerce").fillna(0)
    df["hour_of_day"] = pd.to_numeric(df["hour_of_day"], errors="coerce").fillna(0).astype(int)
    df["date"] = df["created_time"].dt.date.astype(str)
    return df


def viz1_daily_volume(df: pd.DataFrame) -> None:
    daily = (
        df.groupby("date")
        .agg(total_volume=("value_usd", "sum"), trade_count=("trade_id", "count"))
        .reset_index()
    )
    daily["date"] = pd.to_datetime(daily["date"])

    brush = alt.selection_interval(encodings=["x"])

    base = alt.Chart(daily).encode(
        x=alt.X("date:T", title="Date", axis=alt.Axis(format="%b %d")),
    )

    area = base.mark_area(
        line={"color": "#4477AA"},
        color=alt.Gradient(
            gradient="linear",
            stops=[
                alt.GradientStop(color="#4477AA", offset=1),
                alt.GradientStop(color="#4477AA40", offset=0),
            ],
            x1=1, x2=1, y1=1, y2=0,
        ),
        interpolate="monotone",
    ).encode(
        y=alt.Y("total_volume:Q", title="Daily Trade Volume (USD)"),
        tooltip=[
            alt.Tooltip("date:T", title="Date", format="%b %d, %Y"),
            alt.Tooltip("total_volume:Q", title="Volume (USD)", format="$,.0f"),
            alt.Tooltip("trade_count:Q", title="Trades"),
        ],
    ).add_params(brush)

    events_df = pd.DataFrame(EVENTS)
    events_df["date"] = pd.to_datetime(events_df["date"])
    events_df = events_df[
        (events_df["date"] >= daily["date"].min()) & (events_df["date"] <= daily["date"].max())
    ]

    rules = alt.Chart(events_df).mark_rule(
        strokeDash=[4, 4], strokeWidth=1.5, color="#AA3377"
    ).encode(x="date:T")

    labels = alt.Chart(events_df).mark_text(
        align="left", dx=5, dy=-5, fontSize=11, color="#AA3377", fontWeight="bold"
    ).encode(x="date:T", text="label:N")

    detail_area = base.mark_area(
        line={"color": "#4477AA"},
        color="#4477AA40",
        interpolate="monotone",
    ).encode(
        y=alt.Y("total_volume:Q", title="Daily Trade Volume (USD)"),
    ).transform_filter(brush)

    chart = alt.vconcat(
        (area + rules + labels).properties(
            width=700, height=280,
            title="Daily Political Trade Volume Over Time (USD, trades ≥ $2,000)"
        ),
        detail_area.properties(
            width=700, height=120,
            title="Brush above to zoom into a date range"
        ),
    ).resolve_scale(x="shared")

    chart.save(os.path.join(OUT_DIR, "viz1-daily-volume.html"))
    print("  Saved viz1-daily-volume.html")


def viz2_top_markets_stacked(df: pd.DataFrame) -> None:
    by_market = (
        df.groupby(["ticker", "title", "taker_side"])["value_usd"]
        .sum()
        .reset_index()
    )

    totals = by_market.groupby("ticker")["value_usd"].sum().nlargest(12)
    top_tickers = totals.index.tolist()
    top_df = by_market[by_market["ticker"].isin(top_tickers)].copy()

    title_map = top_df.drop_duplicates("ticker").set_index("ticker")["title"].to_dict()
    top_df["short_title"] = top_df["ticker"].map(
        lambda t: (title_map.get(t, t)[:55] + "...") if len(title_map.get(t, t)) > 55 else title_map.get(t, t)
    )

    order = [title_map.get(t, t)[:55] + "..." if len(title_map.get(t, t)) > 55 else title_map.get(t, t)
             for t in totals.index]
    order.reverse()

    selection = alt.selection_point(fields=["taker_side"], bind="legend")

    chart = alt.Chart(top_df).mark_bar().encode(
        y=alt.Y("short_title:N", title=None, sort=order),
        x=alt.X("value_usd:Q", title="Total Trade Volume (USD)", axis=alt.Axis(format="$,.0f")),
        color=alt.Color(
            "taker_side:N",
            title="Taker Side",
            scale=alt.Scale(domain=["yes", "no"], range=YES_NO_COLORS),
        ),
        opacity=alt.condition(selection, alt.value(1), alt.value(0.2)),
        tooltip=[
            alt.Tooltip("short_title:N", title="Market"),
            alt.Tooltip("taker_side:N", title="Side"),
            alt.Tooltip("value_usd:Q", title="Volume (USD)", format="$,.0f"),
        ],
    ).add_params(selection).properties(
        width=600, height=400,
        title="Top 12 Political Markets by Volume (Yes vs No)"
    )

    chart.save(os.path.join(OUT_DIR, "viz2-top-markets.html"))
    print("  Saved viz2-top-markets.html")


def viz3_trade_size_distribution(df: pd.DataFrame) -> None:
    keep_topics = ["Government Shutdown", "Elections & Nominations",
                   "International Affairs", "Executive Orders & Policy"]
    plot_df = df[df["market_topic"].isin(keep_topics)].copy()

    chart = alt.Chart(plot_df).mark_bar(
        opacity=0.75
    ).encode(
        x=alt.X("value_usd:Q", bin=alt.Bin(maxbins=30), title="Trade Value (USD)"),
        y=alt.Y("count():Q", title="Number of Trades"),
        color=alt.Color(
            "market_topic:N",
            title="Market Topic",
            scale=alt.Scale(domain=keep_topics, range=CB_PALETTE[:4]),
        ),
        tooltip=[
            alt.Tooltip("market_topic:N", title="Topic"),
            alt.Tooltip("count():Q", title="Count"),
        ],
    ).properties(
        width=300, height=200,
    ).facet(
        facet=alt.Facet("market_topic:N", title=None),
        columns=2,
    ).resolve_scale(y="independent").properties(
        title="Trade Size Distribution by Market Topic (USD, trades ≥ $2,000)"
    )

    chart.save(os.path.join(OUT_DIR, "viz3-distribution.html"))
    print("  Saved viz3-distribution.html")


def viz4_probability_vs_value(df: pd.DataFrame) -> None:
    plot_df = df[["implied_probability", "value_usd", "count", "market_topic",
                  "title", "ticker", "taker_side", "date"]].copy()
    plot_df = plot_df[plot_df["implied_probability"] > 0]

    brush = alt.selection_interval()

    chart = alt.Chart(plot_df).mark_circle().encode(
        x=alt.X("implied_probability:Q", title="Implied Probability (Yes Price)",
                 scale=alt.Scale(domain=[0, 1])),
        y=alt.Y("value_usd:Q", title="Trade Value (USD)",
                 scale=alt.Scale(type="log")),
        size=alt.Size("count:Q", title="Contract Count",
                      scale=alt.Scale(range=[15, 300])),
        color=alt.condition(
            brush,
            alt.Color("market_topic:N", title="Topic",
                      scale=alt.Scale(range=CB_PALETTE)),
            alt.value("lightgray"),
        ),
        tooltip=[
            alt.Tooltip("title:N", title="Market"),
            alt.Tooltip("implied_probability:Q", title="Implied Prob", format=".0%"),
            alt.Tooltip("value_usd:Q", title="Value (USD)", format="$,.0f"),
            alt.Tooltip("count:Q", title="Contracts"),
            alt.Tooltip("taker_side:N", title="Side"),
            alt.Tooltip("date:N", title="Date"),
        ],
    ).add_params(brush).properties(
        width=700, height=450,
        title="Implied Probability vs Trade Value"
    )

    chart.save(os.path.join(OUT_DIR, "viz4-probability.html"))
    print("  Saved viz4-probability.html")


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    df = load_data()
    print(f"Loaded {len(df)} trades")

    viz1_daily_volume(df)
    viz2_top_markets_stacked(df)
    viz3_trade_size_distribution(df)
    viz4_probability_vs_value(df)

    print("All Altair charts generated.")


if __name__ == "__main__":
    main()
