"""
Chart generation module — WSP design system × neobrutalism.

Produces the 4 required charts for the hedge-fund holdings tracker:
  1. Top-10 Holdings by Filing-Reported Value (horizontal bar)
  2. Portfolio Concentration — top 5 / 10 / 25 / rest (stacked bar or donut)
  3. QoQ Change Attribution — grouped bar (count + USD value)
  4. Put/Call Exposure — horizontal bar (only when put/call rows exist)

All charts are returned as base64-encoded PNG data-URIs for safe inline embedding.
"""

from __future__ import annotations

import base64
import io
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import matplotlib.ticker as mticker
import numpy as np

from .parser import FilingData, HoldingDelta

# ── WSP Palette ───────────────────────────────────────────────────────────────
PAPER = "#FAF6EE"
INK = "#1F1B16"
INK_SOFT = "#4A4239"
INK_MUTE = "#807868"
RULE = "#D9CFB9"
ACCENT = "#B5311A"
POSITIVE = "#1FAE7B"
CODE_BG = "#F1EADC"


def _apply_neobrutalism(ax: plt.Axes, fig: plt.Figure) -> None:
    """Apply neobrutalism styling to a matplotlib axes."""
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)
    for spine in ax.spines.values():
        spine.set_edgecolor(INK)
        spine.set_linewidth(3)
    ax.tick_params(colors=INK_MUTE, labelsize=9)
    ax.xaxis.label.set_color(INK_SOFT)
    ax.yaxis.label.set_color(INK_SOFT)
    ax.title.set_color(INK)
    ax.title.set_fontweight("bold")
    ax.title.set_fontsize(12)
    ax.grid(axis="x", color=RULE, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)


def _to_data_uri(fig: plt.Figure) -> str:
    """Convert a matplotlib figure to a base64 PNG data URI."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _millions_formatter(x: float, pos: int) -> str:
    if x >= 1000:
        return f"${x/1000:.1f}B"
    return f"${x:.0f}M"


# ── Chart 1: Top-10 Holdings ──────────────────────────────────────────────────

def chart_top10_holdings(data: FilingData, title: str = "Top-10 Holdings by Filing-Reported Value") -> str:
    """Horizontal bar chart — top 10 positions by filing-reported value in USD millions."""
    top10 = sorted(data.holdings, key=lambda h: h.value_usd_thousands, reverse=True)[:10]
    if not top10:
        return ""

    labels = [h.label for h in reversed(top10)]
    values = [h.value_usd_millions for h in reversed(top10)]

    fig, ax = plt.subplots(figsize=(10, 6))
    _apply_neobrutalism(ax, fig)

    bars = ax.barh(labels, values, color=ACCENT, edgecolor=INK, linewidth=1.5, zorder=3)

    # Value annotations
    for bar, val in zip(bars, values):
        ax.text(
            val + max(values) * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"${val:,.0f}M",
            va="center",
            ha="left",
            color=INK_SOFT,
            fontsize=8,
            fontfamily="monospace",
        )

    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_millions_formatter))
    ax.set_xlabel("Filing-Reported Value (USD Millions)", fontsize=10, color=INK_SOFT)
    ax.set_title(title, fontsize=13, color=INK, pad=14)
    ax.tick_params(axis="y", labelsize=8)

    # Hard offset shadow border effect (neobrutalism)
    fig.subplots_adjust(left=0.3, right=0.92, top=0.88, bottom=0.1)
    return _to_data_uri(fig)


# ── Chart 2: Portfolio Concentration ──────────────────────────────────────────

def chart_concentration(data: FilingData, title: str = "Portfolio Concentration") -> str:
    """
    Donut chart showing top-5 / top-10 / top-25 / remainder share
    of total filing-reported value.
    """
    sorted_holdings = sorted(data.holdings, key=lambda h: h.value_usd_thousands, reverse=True)
    total = data.total_value_usd_thousands
    if total == 0:
        return ""

    def pct_sum(start: int, end: int) -> float:
        subset = sorted_holdings[start:end]
        return sum(h.value_usd_thousands for h in subset) / total * 100

    top5 = pct_sum(0, 5)
    top10_marginal = pct_sum(5, 10)
    top25_marginal = pct_sum(10, 25)
    rest = 100 - top5 - top10_marginal - top25_marginal

    sizes = [top5, top10_marginal, top25_marginal, max(rest, 0)]
    labels_raw = ["Top 5", "Top 6–10", "Top 11–25", "Rest"]
    colors = [ACCENT, INK_SOFT, INK_MUTE, RULE]

    # Filter zero slices
    filtered = [(s, l, c) for s, l, c in zip(sizes, labels_raw, colors) if s > 0]
    if not filtered:
        return ""
    sizes_f, labels_f, colors_f = zip(*filtered)

    fig, ax = plt.subplots(figsize=(8, 7))
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)

    wedges, texts, autotexts = ax.pie(
        sizes_f,
        labels=None,
        colors=colors_f,
        autopct="%1.1f%%",
        startangle=90,
        wedgeprops={"edgecolor": INK, "linewidth": 2.5},
        pctdistance=0.75,
    )

    for t in autotexts:
        t.set_color(PAPER)
        t.set_fontsize(10)
        t.set_fontweight("bold")

    # Draw inner circle for donut effect
    centre_circle = plt.Circle((0, 0), 0.5, fc=PAPER, ec=INK, linewidth=3)
    ax.add_artist(centre_circle)

    # Legend
    patches = [mpatches.Patch(color=c, label=f"{l} ({s:.1f}%)")
               for c, l, s in zip(colors_f, labels_f, sizes_f)]
    ax.legend(handles=patches, loc="lower center", bbox_to_anchor=(0.5, -0.15),
              ncol=2, frameon=True, edgecolor=INK, facecolor=PAPER,
              labelcolor=INK_SOFT, fontsize=10)

    ax.set_title(title, fontsize=13, color=INK, fontweight="bold", pad=14)
    fig.subplots_adjust(top=0.88, bottom=0.15)
    return _to_data_uri(fig)


# ── Chart 3: QoQ Change Attribution ───────────────────────────────────────────

def chart_qoq_attribution(
    deltas: list[HoldingDelta],
    title: str = "Quarter-over-Quarter Change Attribution",
) -> str:
    """
    Grouped bar chart: 4 categories × 2 bars each (count and USD value).
    Categories: New Positions | Exits | Largest Adds | Largest Trims
    """
    new = [d for d in deltas if d.change_type == "new"]
    exits = [d for d in deltas if d.change_type == "exit"]
    adds = [d for d in deltas if d.change_type == "add"]
    trims = [d for d in deltas if d.change_type == "trim"]

    def total_val(lst: list[HoldingDelta]) -> float:
        return abs(sum(d.value_change_usd_thousands for d in lst)) / 1000  # → millions

    counts = [len(new), len(exits), len(adds), len(trims)]
    values = [
        sum(d.current.value_usd_thousands for d in new if d.current) / 1000,
        sum(d.prior.value_usd_thousands for d in exits if d.prior) / 1000,
        total_val(adds),
        total_val(trims),
    ]

    cats = ["New Positions", "Exits", "Adds", "Trims"]
    bar_colors_count = [POSITIVE, ACCENT, POSITIVE, ACCENT]
    bar_colors_val = [POSITIVE, ACCENT, POSITIVE, ACCENT]

    x = np.arange(len(cats))
    width = 0.35

    fig, ax1 = plt.subplots(figsize=(10, 6))
    _apply_neobrutalism(ax1, fig)

    ax2 = ax1.twinx()
    ax2.set_facecolor(PAPER)
    ax2.spines["right"].set_edgecolor(INK)
    ax2.spines["right"].set_linewidth(3)
    ax2.tick_params(colors=INK_MUTE, labelsize=9)

    bars1 = ax1.bar(x - width / 2, counts, width, label="Count",
                    color=bar_colors_count, edgecolor=INK, linewidth=1.5, zorder=3)
    bars2 = ax2.bar(x + width / 2, values, width, label="Value (USD M)",
                    color=bar_colors_val, edgecolor=INK, linewidth=1.5,
                    alpha=0.75, zorder=3)

    ax1.set_ylabel("Number of Positions", color=INK_SOFT, fontsize=10)
    ax2.set_ylabel("Filing-Reported Value (USD Millions)", color=INK_SOFT, fontsize=10)
    ax1.set_xticks(x)
    ax1.set_xticklabels(cats, fontsize=10, color=INK_SOFT)
    ax1.set_title(title, fontsize=13, color=INK, fontweight="bold", pad=14)

    # Annotate counts
    for bar, val in zip(bars1, counts):
        if val:
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.2,
                     str(val), ha="center", va="bottom", fontsize=9, color=INK)

    # Annotate values
    for bar, val in zip(bars2, values):
        if val:
            ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.01,
                     f"${val:,.0f}M", ha="center", va="bottom", fontsize=8,
                     color=INK, fontfamily="monospace")

    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color=POSITIVE, lw=4, label="New / Adds"),
        Line2D([0], [0], color=ACCENT, lw=4, label="Exits / Trims"),
        mpatches.Patch(facecolor=PAPER, edgecolor=INK, linewidth=1.5, label="Solid = Count"),
        mpatches.Patch(facecolor=PAPER, edgecolor=INK, linewidth=1.5, alpha=0.75, label="Faded = USD Value"),
    ]
    ax1.legend(handles=legend_elements, loc="upper right", frameon=True,
               edgecolor=INK, facecolor=PAPER, labelcolor=INK_SOFT, fontsize=9)

    fig.subplots_adjust(top=0.88, bottom=0.12, left=0.08, right=0.88)
    return _to_data_uri(fig)


# ── Chart 4: Put/Call Exposure ─────────────────────────────────────────────────

def chart_put_call_exposure(
    data: FilingData,
    title: str = "Put/Call Exposure",
    max_positions: int = 20,
) -> Optional[str]:
    """
    Horizontal grouped bar showing Put and Call value per issuer.
    Returns None if the filing has no put/call rows.
    """
    pc_holdings = [h for h in data.holdings if h.put_call in ("Put", "Call")]
    if not pc_holdings:
        return None

    # Aggregate by issuer
    agg: dict[str, dict[str, float]] = {}
    for h in pc_holdings:
        key = h.issuer_name
        if key not in agg:
            agg[key] = {"Put": 0.0, "Call": 0.0}
        agg[key][h.put_call] += h.value_usd_millions

    # Sort by total exposure
    sorted_agg = sorted(agg.items(), key=lambda kv: sum(kv[1].values()), reverse=True)
    sorted_agg = sorted_agg[:max_positions]
    sorted_agg = list(reversed(sorted_agg))

    issuers = [k for k, _ in sorted_agg]
    put_vals = [v.get("Put", 0) for _, v in sorted_agg]
    call_vals = [v.get("Call", 0) for _, v in sorted_agg]

    n = len(issuers)
    y = np.arange(n)
    height = 0.35

    fig, ax = plt.subplots(figsize=(10, max(5, n * 0.5 + 2)))
    _apply_neobrutalism(ax, fig)

    ax.barh(y + height / 2, put_vals, height, label="Put", color=ACCENT,
            edgecolor=INK, linewidth=1.5, zorder=3)
    ax.barh(y - height / 2, call_vals, height, label="Call", color=POSITIVE,
            edgecolor=INK, linewidth=1.5, zorder=3)

    ax.set_yticks(y)
    ax.set_yticklabels(issuers, fontsize=8)
    ax.set_xlabel("Filing-Reported Value (USD Millions)", color=INK_SOFT, fontsize=10)
    ax.set_title(title, fontsize=13, color=INK, fontweight="bold", pad=14)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_millions_formatter))

    ax.legend(frameon=True, edgecolor=INK, facecolor=PAPER, labelcolor=INK_SOFT, fontsize=10)
    fig.subplots_adjust(left=0.3, right=0.92, top=0.88, bottom=0.1)
    return _to_data_uri(fig)


# ── Convenience builder ───────────────────────────────────────────────────────

def build_all_charts(
    current: FilingData,
    deltas: Optional[list[HoldingDelta]],
    filer_name: str = "",
    period: str = "",
) -> dict[str, Optional[str]]:
    """
    Build all applicable charts and return a dict of name → data-URI.
    ``deltas`` may be None if this is a single-period run (no prior quarter).
    """
    suffix = f"— {filer_name} ({period})" if filer_name else ""

    charts: dict[str, Optional[str]] = {}
    charts["top10"] = chart_top10_holdings(
        current, f"Top-10 Holdings by Filing-Reported Value {suffix}".strip()
    )
    charts["concentration"] = chart_concentration(
        current, f"Portfolio Concentration {suffix}".strip()
    )

    if deltas:
        charts["qoq"] = chart_qoq_attribution(
            deltas, f"Quarter-over-Quarter Change Attribution {suffix}".strip()
        )
    else:
        charts["qoq"] = None

    charts["put_call"] = chart_put_call_exposure(
        current, f"Put/Call Exposure {suffix}".strip()
    )

    return charts
