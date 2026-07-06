"""Generate WSP-palette neobrutalism charts as PNG bytes."""

from __future__ import annotations

import base64
import io
import matplotlib.pyplot as plt

from compare_holdings import ComparisonSummary, concentration_buckets
from parse_13f import Holding, HoldingsSnapshot
from wsp_palette import ACCENT, INK, INK_MUTE, INK_SOFT, PAPER, POSITIVE, RULE


def _style_axes(ax: plt.Axes) -> None:
    ax.set_facecolor(PAPER)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(RULE)
    ax.spines["bottom"].set_color(RULE)
    ax.tick_params(colors=INK_MUTE, labelsize=9)
    ax.title.set_color(INK)
    ax.title.set_fontweight("bold")
    ax.title.set_fontsize(11)


def _chart_card(fig: plt.Figure) -> None:
    fig.patch.set_facecolor(PAPER)
    for ax in fig.axes:
        _style_axes(ax)


def _to_base64_png(fig: plt.Figure) -> str:
    buffer = io.BytesIO()
    fig.savefig(
        buffer,
        format="png",
        dpi=160,
        bbox_inches="tight",
        facecolor=PAPER,
        edgecolor=INK,
    )
    plt.close(fig)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def chart_top10_holdings(snapshot: HoldingsSnapshot) -> str:
    top = snapshot.top_by_value(10)
    if not top:
        raise ValueError("No holdings available for top-10 chart")

    labels = [
        f"{h.issuer_name[:28]}{'…' if len(h.issuer_name) > 28 else ''}"
        for h in reversed(top)
    ]
    values = [h.value_usd / 1_000 for h in reversed(top)]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.barh(labels, values, color=ACCENT, edgecolor=INK, linewidth=1.5)
    ax.set_xlabel("Filing-reported value (USD thousands)", color=INK_MUTE, fontsize=9)
    ax.set_title("Top-10 Holdings by Filing-Reported Value")
    _chart_card(fig)
    for bar in bars:
        bar.set_linewidth(1.5)
    return _to_base64_png(fig)


def chart_concentration(snapshot: HoldingsSnapshot) -> str:
    buckets = concentration_buckets(snapshot)
    labels = ["Top 5", "Top 6-10", "Top 11-25", "Remainder"]
    sizes = [
        buckets["top5_pct"],
        buckets["top10_pct"],
        buckets["top25_pct"],
        buckets["remainder_pct"],
    ]
    colors = [ACCENT, INK_SOFT, INK_MUTE, RULE]

    fig, ax = plt.subplots(figsize=(6, 5))
    wedges, _, autotexts = ax.pie(
        sizes,
        labels=labels,
        colors=colors,
        autopct="%1.1f%%",
        startangle=90,
        wedgeprops={"edgecolor": INK, "linewidth": 2},
        textprops={"color": INK, "fontsize": 9},
    )
    for text in autotexts:
        text.set_color(INK)
        text.set_fontsize(8)
    ax.set_title("Portfolio Concentration")
    _chart_card(fig)
    return _to_base64_png(fig)


def chart_qoq_changes(comparison: ComparisonSummary) -> str:
    categories = ["New", "Exits", "Adds", "Trims"]
    counts = [
        len(comparison.new_positions),
        len(comparison.exits),
        len(comparison.adds),
        len(comparison.trims),
    ]
    values = [
        sum(c.current_value for c in comparison.new_positions) / 1_000_000,
        sum(c.prior_value for c in comparison.exits) / 1_000_000,
        sum(c.value_delta for c in comparison.adds) / 1_000_000,
        abs(sum(c.value_delta for c in comparison.trims)) / 1_000_000,
    ]

    x = range(len(categories))
    width = 0.35
    fig, ax1 = plt.subplots(figsize=(8, 5))
    ax2 = ax1.twinx()

    bars1 = ax1.bar(
        [i - width / 2 for i in x],
        counts,
        width,
        label="Count",
        color=POSITIVE,
        edgecolor=INK,
        linewidth=1.5,
    )
    bars2 = ax2.bar(
        [i + width / 2 for i in x],
        values,
        width,
        label="Value ($M)",
        color=ACCENT,
        edgecolor=INK,
        linewidth=1.5,
    )

    ax1.set_xticks(list(x), categories)
    ax1.set_ylabel("Count", color=INK_MUTE, fontsize=9)
    ax2.set_ylabel("Absolute value change ($M)", color=INK_MUTE, fontsize=9)
    ax1.set_title("QoQ Change Attribution")
    _chart_card(fig)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_color(RULE)
    ax2.tick_params(colors=INK_MUTE, labelsize=9)
    for bar in list(bars1) + list(bars2):
        bar.set_linewidth(1.5)
    return _to_base64_png(fig)


def chart_put_call_exposure(holdings: list[Holding]) -> str | None:
    option_rows = [h for h in holdings if h.is_put_call]
    if not option_rows:
        return None

    by_issuer: dict[str, dict[str, int]] = {}
    for row in option_rows:
        bucket = by_issuer.setdefault(row.issuer_name, {"PUT": 0, "CALL": 0})
        bucket[row.put_call.upper()] += row.value_usd

    issuers = sorted(
        by_issuer,
        key=lambda name: by_issuer[name]["PUT"] + by_issuer[name]["CALL"],
        reverse=True,
    )[:10]
    issuers = list(reversed(issuers))
    puts = [by_issuer[i]["PUT"] / 1_000 for i in issuers]
    calls = [by_issuer[i]["CALL"] / 1_000 for i in issuers]

    fig, ax = plt.subplots(figsize=(8, 5))
    y = range(len(issuers))
    ax.barh(
        [i - 0.2 for i in y],
        puts,
        height=0.35,
        color=ACCENT,
        edgecolor=INK,
        linewidth=1.5,
        label="Put",
    )
    ax.barh(
        [i + 0.2 for i in y],
        calls,
        height=0.35,
        color=POSITIVE,
        edgecolor=INK,
        linewidth=1.5,
        label="Call",
    )
    ax.set_yticks(list(y), issuers)
    ax.set_xlabel("Filing-reported value (USD thousands)", color=INK_MUTE, fontsize=9)
    ax.set_title("Put/Call Exposure")
    ax.legend(frameon=False)
    _chart_card(fig)
    return _to_base64_png(fig)


def build_chart_set(
    current: HoldingsSnapshot,
    comparison: ComparisonSummary | None,
) -> dict[str, str]:
    charts: dict[str, str] = {
        "top10": chart_top10_holdings(current),
        "concentration": chart_concentration(current),
    }
    if comparison is not None:
        charts["qoq"] = chart_qoq_changes(comparison)
    put_call = chart_put_call_exposure(current.holdings)
    if put_call:
        charts["put_call"] = put_call
    return charts
