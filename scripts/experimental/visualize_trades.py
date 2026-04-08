import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.colors import LinearSegmentedColormap

plt.rcParams.update({
    'figure.facecolor': '#0e1117',
    'axes.facecolor': '#161b22',
    'axes.edgecolor': '#30363d',
    'axes.labelcolor': '#c9d1d9',
    'text.color': '#c9d1d9',
    'xtick.color': '#8b949e',
    'ytick.color': '#8b949e',
    'grid.color': '#21262d',
    'font.family': 'sans-serif',
    'font.size': 11,
})

ACCENT = '#58a6ff'
ACCENT2 = '#f78166'
ACCENT3 = '#7ee787'
GREEN = '#3fb950'
RED = '#f85149'

df = pd.read_csv('/Users/eliholmes/kalshi/political_500_2k_with_titles.csv')

# Derive the implied odds the taker accepted
df['taker_odds'] = np.where(df['taker_side'] == 'yes', df['yes_price'], df['no_price'])
df['taker_odds_pct'] = df['taker_odds']  # already 0-100

# ── FIGURE 1: Trade Size Distribution (log-scale bins) ──────────────────────
fig1, ax1 = plt.subplots(figsize=(14, 7))

bins = [500, 750, 1000, 1500, 2000, 3000, 5000, 7500,
        10000, 15000, 20000, 30000, 50000, 75000, 100000, df['value_usd'].max() + 1]
bin_labels = ['$500-750', '$750-1K', '$1K-1.5K', '$1.5K-2K', '$2K-3K',
              '$3K-5K', '$5K-7.5K', '$7.5K-10K', '$10K-15K', '$15K-20K',
              '$20K-30K', '$30K-50K', '$50K-75K', '$75K-100K', '$100K+']

counts, _ = np.histogram(df['value_usd'], bins=bins)

colors = plt.cm.cool(np.linspace(0.15, 0.85, len(counts)))

bars = ax1.bar(range(len(counts)), counts, color=colors, edgecolor='#30363d',
               linewidth=0.5, width=0.82, zorder=3)

for bar, c in zip(bars, counts):
    if c > 0:
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 3,
                 str(c), ha='center', va='bottom', fontsize=9, fontweight='bold',
                 color='#c9d1d9')

ax1.set_xticks(range(len(bin_labels)))
ax1.set_xticklabels(bin_labels, rotation=40, ha='right', fontsize=9)
ax1.set_ylabel('Number of Trades', fontsize=13, fontweight='bold')
ax1.set_title('Kalshi Political Trades — Size Distribution ($500+ Minimum)',
              fontsize=16, fontweight='bold', pad=18, color='white')
ax1.grid(axis='y', alpha=0.3, zorder=0)
ax1.set_axisbelow(True)

total_vol = df['value_usd'].sum()
median_val = df['value_usd'].median()
mean_val = df['value_usd'].mean()
stats_text = (f'Total Volume: ${total_vol:,.0f}   |   '
              f'Median Trade: ${median_val:,.0f}   |   '
              f'Mean Trade: ${mean_val:,.0f}   |   '
              f'Trades: {len(df):,}')
ax1.text(0.5, -0.22, stats_text, transform=ax1.transAxes, ha='center',
         fontsize=10, color='#8b949e', style='italic')

fig1.tight_layout(rect=[0, 0.05, 1, 1])
fig1.savefig('/Users/eliholmes/kalshi/trade_size_distribution.png', dpi=180, bbox_inches='tight')
print("✓ Saved trade_size_distribution.png")


# ── FIGURE 2: Implied Odds / Risk Profile ───────────────────────────────────
fig2, axes = plt.subplots(2, 2, figsize=(16, 12),
                          gridspec_kw={'hspace': 0.38, 'wspace': 0.28})

# ─── 2a: Histogram of taker implied odds ────────────────────────────────────
ax2a = axes[0, 0]
odds_bins = np.arange(0, 105, 5)

yes_mask = df['taker_side'] == 'yes'
ax2a.hist(df.loc[yes_mask, 'taker_odds_pct'], bins=odds_bins, alpha=0.8,
          color=GREEN, edgecolor='#30363d', linewidth=0.5, label='Yes Taker', zorder=3)
ax2a.hist(df.loc[~yes_mask, 'taker_odds_pct'], bins=odds_bins, alpha=0.65,
          color=RED, edgecolor='#30363d', linewidth=0.5, label='No Taker', zorder=3)

ax2a.set_xlabel('Implied Probability (%)', fontsize=11, fontweight='bold')
ax2a.set_ylabel('Number of Trades', fontsize=11, fontweight='bold')
ax2a.set_title('What Odds Are Traders Taking?', fontsize=14, fontweight='bold', color='white')
ax2a.legend(framealpha=0.3, edgecolor='#30363d')
ax2a.grid(axis='y', alpha=0.3, zorder=0)

# ─── 2b: Trade Size vs Implied Odds scatter ─────────────────────────────────
ax2b = axes[0, 1]

scatter_colors = np.where(df['taker_side'] == 'yes', GREEN, RED)
ax2b.scatter(df['taker_odds_pct'], df['value_usd'], c=scatter_colors,
             alpha=0.4, s=18, edgecolors='none', zorder=3)
ax2b.set_yscale('log')
ax2b.set_xlabel('Implied Probability Taken (%)', fontsize=11, fontweight='bold')
ax2b.set_ylabel('Trade Value (USD, log scale)', fontsize=11, fontweight='bold')
ax2b.set_title('Trade Size vs Implied Probability', fontsize=14, fontweight='bold', color='white')
ax2b.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'${x:,.0f}'))
ax2b.grid(alpha=0.2, zorder=0)

from matplotlib.lines import Line2D
legend_els = [Line2D([0], [0], marker='o', color='w', markerfacecolor=GREEN, markersize=8, label='Yes Taker'),
              Line2D([0], [0], marker='o', color='w', markerfacecolor=RED, markersize=8, label='No Taker')]
ax2b.legend(handles=legend_els, framealpha=0.3, edgecolor='#30363d')

# ─── 2c: Risk appetite breakdown (long-shot vs. favorite) ───────────────────
ax2c = axes[1, 0]

risk_bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
risk_labels = ['0-10%', '10-20%', '20-30%', '30-40%', '40-50%',
               '50-60%', '60-70%', '70-80%', '80-90%', '90-100%']

df['odds_bin'] = pd.cut(df['taker_odds_pct'], bins=risk_bins, labels=risk_labels, right=True)
vol_by_bin = df.groupby('odds_bin', observed=False)['value_usd'].sum() / 1000

cmap_risk = plt.cm.RdYlGn_r
colors_risk = cmap_risk(np.linspace(0.1, 0.9, len(vol_by_bin)))

bars_risk = ax2c.bar(range(len(vol_by_bin)), vol_by_bin.values, color=colors_risk,
                     edgecolor='#30363d', linewidth=0.5, width=0.82, zorder=3)

for bar, v in zip(bars_risk, vol_by_bin.values):
    if v > 0:
        ax2c.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                  f'${v:,.0f}K', ha='center', va='bottom', fontsize=8,
                  fontweight='bold', color='#c9d1d9')

ax2c.set_xticks(range(len(risk_labels)))
ax2c.set_xticklabels(risk_labels, rotation=40, ha='right', fontsize=9)
ax2c.set_ylabel('Total Volume ($K)', fontsize=11, fontweight='bold')
ax2c.set_title('Volume by Implied Probability Bucket\n(How much money at each risk level?)',
               fontsize=13, fontweight='bold', color='white')
ax2c.grid(axis='y', alpha=0.3, zorder=0)

# ─── 2d: Top traded markets by volume ───────────────────────────────────────
ax2d = axes[1, 1]

top_markets = (df.groupby('title')
               .agg(total_vol=('value_usd', 'sum'), trades=('trade_id', 'count'),
                    avg_odds=('taker_odds_pct', 'mean'))
               .sort_values('total_vol', ascending=False)
               .head(12))

# Truncate long titles
short_titles = [t[:48] + '…' if len(t) > 48 else t for t in top_markets.index]

y_pos = np.arange(len(top_markets))
bar_colors = plt.cm.cool(np.linspace(0.2, 0.8, len(top_markets)))

ax2d.barh(y_pos, top_markets['total_vol'] / 1000, color=bar_colors,
          edgecolor='#30363d', linewidth=0.5, height=0.72, zorder=3)

for i, (vol, trades) in enumerate(zip(top_markets['total_vol'], top_markets['trades'])):
    ax2d.text(vol / 1000 + 1, i, f'${vol/1000:,.0f}K  ({trades} trades)',
              va='center', fontsize=8, color='#8b949e')

ax2d.set_yticks(y_pos)
ax2d.set_yticklabels(short_titles, fontsize=8.5)
ax2d.invert_yaxis()
ax2d.set_xlabel('Total Volume ($K)', fontsize=11, fontweight='bold')
ax2d.set_title('Top 12 Markets by Volume', fontsize=14, fontweight='bold', color='white')
ax2d.grid(axis='x', alpha=0.2, zorder=0)

fig2.suptitle('Kalshi Political Trades — Implied Risk & Odds Analysis',
              fontsize=17, fontweight='bold', color='white', y=1.01)
fig2.savefig('/Users/eliholmes/kalshi/implied_risk_analysis.png', dpi=180, bbox_inches='tight')
print("✓ Saved implied_risk_analysis.png")

print("\nDone — two charts saved.")
