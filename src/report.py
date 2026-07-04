"""
Report generator — PDF, Markdown memo, and CSV output.

Produces:
  <output_dir>/
    <slug>-holdings-report.pdf   — PDF with 4 embedded charts
    <slug>-holdings-memo.md      — Markdown research memo
    <slug>-holdings-table.csv    — Full information table CSV
"""

from __future__ import annotations

import base64
import csv
import os
import pathlib
import re
from typing import Optional

from jinja2 import Environment, FileSystemLoader

from .edgar import FilingRecord
from .parser import FilingData, HoldingDelta, Holding
from .charts import build_all_charts

# ── Constants ─────────────────────────────────────────────────────────────────

DISCLAIMER_TEXT = (
    "This report is produced for informational and research purposes only. "
    "All holdings data is sourced from public SEC EDGAR 13F filings, which are reported "
    "with a 45-day delay and exclude shorts, hedges, cash, private holdings, derivatives "
    "detail, and intraperiod trading. This does not constitute investment advice. "
    "Past portfolio positioning is not indicative of future financial results. "
    "All trademarks are the property of their respective owners."
)

REQUIRED_CTA = (
    "This skill was engineered by Wall Street Prompt. "
    "Learn how to use AI for investing at [wallstreetprompt.com](https://wallstreetprompt.com)."
)

_SKILL_DIR = pathlib.Path(__file__).parent.parent  # workspace root
_ASSETS_DIR = _SKILL_DIR / "assets"
_WSP_LOGO = _ASSETS_DIR / "wsp_logo.png"


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _concentration(data: FilingData, top_n: int) -> float:
    sorted_h = sorted(data.holdings, key=lambda h: h.value_usd_thousands, reverse=True)
    total = data.total_value_usd_thousands
    if total == 0:
        return 0.0
    subset_val = sum(h.value_usd_thousands for h in sorted_h[:top_n])
    return subset_val / total * 100


def _logo_data_uri() -> str:
    """Load WSP logo from bundled assets and return a base64 data URI."""
    if _WSP_LOGO.exists():
        data = _WSP_LOGO.read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        return f"data:image/png;base64,{b64}"
    return ""  # no logo available — avoid external URL


# ── PDF ───────────────────────────────────────────────────────────────────────

def generate_pdf(
    filing: FilingRecord,
    current: FilingData,
    prior: Optional[FilingData],
    prior_filing: Optional[FilingRecord],
    output_path: pathlib.Path,
) -> None:
    """Render the full PDF report with embedded charts."""
    from weasyprint import HTML, CSS

    deltas: Optional[list[HoldingDelta]] = None
    if prior is not None:
        from .parser import compare_filings
        deltas = compare_filings(current, prior)

    charts = build_all_charts(
        current,
        deltas,
        filer_name=filing.filer_name,
        period=filing.period_of_report,
    )

    sorted_holdings = sorted(current.holdings, key=lambda h: h.value_usd_thousands, reverse=True)
    top_50 = sorted_holdings[:50]

    new_positions = sorted(
        [d for d in (deltas or []) if d.change_type == "new"],
        key=lambda d: (d.current.value_usd_thousands if d.current else 0),
        reverse=True,
    )
    exits = sorted(
        [d for d in (deltas or []) if d.change_type == "exit"],
        key=lambda d: (d.prior.value_usd_thousands if d.prior else 0),
        reverse=True,
    )
    adds = sorted(
        [d for d in (deltas or []) if d.change_type == "add"],
        key=lambda d: abs(d.value_change_usd_thousands),
        reverse=True,
    )[:20]
    trims = sorted(
        [d for d in (deltas or []) if d.change_type == "trim"],
        key=lambda d: abs(d.value_change_usd_thousands),
        reverse=True,
    )[:20]

    env = Environment(
        loader=FileSystemLoader(str(pathlib.Path(__file__).parent / "templates")),
        autoescape=True,
    )
    template = env.get_template("report.html")

    html_str = template.render(
        filer_name=filing.filer_name,
        cik=filing.cik,
        form_type=filing.form_type,
        period_of_report=filing.period_of_report,
        filed_date=filing.filed_date,
        accession_number=filing.accession_number,
        is_amendment=filing.is_amendment,
        edgar_url=filing.edgar_url or f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={filing.cik}&type=13F-HR&dateb=&owner=include&count=40",
        total_value_millions=current.total_value_usd_millions,
        total_value_thousands=current.total_value_usd_thousands,
        holding_count=current.holding_count,
        top5_pct=_concentration(current, 5),
        top10_pct=_concentration(current, 10),
        charts=charts,
        top_holdings=top_50,
        all_holdings=sorted_holdings,
        deltas=deltas,
        prior_period=prior_filing.period_of_report if prior_filing else "",
        new_positions=new_positions,
        exits=exits,
        adds=adds,
        trims=trims,
        wsp_logo_uri=_logo_data_uri(),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html_str, base_url=str(_SKILL_DIR)).write_pdf(str(output_path))
    print(f"  PDF saved → {output_path}")


# ── Markdown Memo ─────────────────────────────────────────────────────────────

def generate_markdown(
    filing: FilingRecord,
    current: FilingData,
    prior: Optional[FilingData],
    prior_filing: Optional[FilingRecord],
    output_path: pathlib.Path,
) -> None:
    """Generate a structured markdown research memo."""
    deltas: Optional[list[HoldingDelta]] = None
    if prior is not None:
        from .parser import compare_filings
        deltas = compare_filings(current, prior)

    sorted_h = sorted(current.holdings, key=lambda h: h.value_usd_thousands, reverse=True)
    total = current.total_value_usd_thousands
    top5_pct = _concentration(current, 5)
    top10_pct = _concentration(current, 10)

    lines: list[str] = []

    def w(*args: str) -> None:
        lines.extend(args)
        lines.append("")

    edgar_link = (
        filing.edgar_url
        or f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={filing.cik}&type=13F-HR&dateb=&owner=include&count=40"
    )

    w(f"# {filing.filer_name} — 13F Holdings Report",
      f"**Reporting Period:** {filing.period_of_report}  ",
      f"**Filed:** {filing.filed_date}")

    # ── Audit Trail ──────────────────────────────────────────────────────────
    w("---", "## Filer & Filing Audit Trail")
    w(
        f"| Field | Value |",
        f"|---|---|",
        f"| Legal Filer | {filing.filer_name} |",
        f"| CIK | `{filing.cik}` |",
        f"| Filing Type | {filing.form_type}{' (Amendment)' if filing.is_amendment else ''} |",
        f"| Reporting Period | {filing.period_of_report} |",
        f"| Filing Date | {filing.filed_date} |",
        f"| Accession Number | `{filing.accession_number}` |",
        f"| Amendment Status | {'Amendment filing' if filing.is_amendment else 'Original filing'} |",
        f"| EDGAR Filing | [{edgar_link}]({edgar_link}) |",
    )

    # ── Executive Snapshot ───────────────────────────────────────────────────
    w("---", "## Executive Research Snapshot")
    w(
        f"| Metric | Value |",
        f"|---|---|",
        f"| Total 13F Reported Value | ${current.total_value_usd_millions:,.1f}M |",
        f"| Number of Positions | {current.holding_count:,} |",
        f"| Top-5 Concentration | {top5_pct:.1f}% of reported portfolio |",
        f"| Top-10 Concentration | {top10_pct:.1f}% of reported portfolio |",
        f"| Has Put/Call Rows | {'Yes' if current.has_put_call else 'No'} |",
    )

    # ── Top Holdings ─────────────────────────────────────────────────────────
    w("---", "## Top-10 Holdings by Filing-Reported Value")
    w(
        "| # | Issuer | CUSIP | Value (USD M) | Shares / Principal | Type | Put/Call | % Portfolio |",
        "|---|---|---|---|---|---|---|---|",
    )
    for i, h in enumerate(sorted_h[:10], 1):
        pct = h.value_usd_thousands / total * 100 if total else 0
        ticker_str = f" `{h.ticker}`" if h.ticker else ""
        w(
            f"| {i} | {h.issuer_name}{ticker_str} | `{h.cusip}` "
            f"| ${h.value_usd_millions:,.2f}M | {h.shares_or_principal:,} "
            f"| {h.share_type} | {h.put_call or '—'} | {pct:.2f}% |",
        )

    # ── Concentration ─────────────────────────────────────────────────────────
    w("---", "## Portfolio Concentration")
    top25_pct = _concentration(current, 25)
    w(
        f"| Bucket | Positions | Filing-Reported Value Share |",
        f"|---|---|---|",
        f"| Top 5 | 5 | {top5_pct:.1f}% |",
        f"| Top 10 | 10 | {top10_pct:.1f}% |",
        f"| Top 25 | 25 | {top25_pct:.1f}% |",
        f"| Rest | {max(0, current.holding_count - 25)} | {max(0.0, 100 - top25_pct):.1f}% |",
    )

    # ── QoQ Changes ──────────────────────────────────────────────────────────
    if deltas and prior_filing:
        new_pos = sorted(
            [d for d in deltas if d.change_type == "new"],
            key=lambda d: (d.current.value_usd_thousands if d.current else 0),
            reverse=True,
        )
        exits = sorted(
            [d for d in deltas if d.change_type == "exit"],
            key=lambda d: (d.prior.value_usd_thousands if d.prior else 0),
            reverse=True,
        )
        adds = sorted(
            [d for d in deltas if d.change_type == "add"],
            key=lambda d: abs(d.value_change_usd_thousands),
            reverse=True,
        )[:20]
        trims = sorted(
            [d for d in deltas if d.change_type == "trim"],
            key=lambda d: abs(d.value_change_usd_thousands),
            reverse=True,
        )[:20]

        w("---", f"## Quarter-over-Quarter Changes vs. {prior_filing.period_of_report}")
        w(
            f"| Change Type | Count | Total Value Impact (USD M) |",
            f"|---|---|---|",
            f"| New Positions | {len(new_pos)} | ${sum(d.current.value_usd_thousands for d in new_pos if d.current)/1000:,.1f}M |",
            f"| Exits | {len(exits)} | ${sum(d.prior.value_usd_thousands for d in exits if d.prior)/1000:,.1f}M |",
            f"| Adds | {len(adds)} | ${abs(sum(d.value_change_usd_thousands for d in adds))/1000:,.1f}M |",
            f"| Trims | {len(trims)} | ${abs(sum(d.value_change_usd_thousands for d in trims))/1000:,.1f}M |",
        )

        if new_pos:
            w("### New Positions")
            w("| Issuer | CUSIP | Value (USD M) | Shares |",
              "|---|---|---|---|")
            for d in new_pos:
                w(f"| {d.label} | `{d.cusip}` | ${d.current.value_usd_millions:,.2f}M | {d.current.shares_or_principal:,} |")

        if exits:
            w("### Exits")
            w("| Issuer | CUSIP | Prior Value (USD M) | Prior Shares |",
              "|---|---|---|---|")
            for d in exits:
                w(f"| {d.label} | `{d.cusip}` | ${d.prior.value_usd_millions:,.2f}M | {d.prior.shares_or_principal:,} |")

        if adds:
            w("### Largest Adds")
            w("| Issuer | CUSIP | Shares Added | Value Change (USD M) | Current Value (USD M) |",
              "|---|---|---|---|---|")
            for d in adds:
                w(f"| {d.label} | `{d.cusip}` | +{d.shares_change:,} | +${d.value_change_usd_thousands/1000:,.2f}M | ${d.current.value_usd_millions:,.2f}M |")

        if trims:
            w("### Largest Trims")
            w("| Issuer | CUSIP | Shares Trimmed | Value Change (USD M) | Current Value (USD M) |",
              "|---|---|---|---|---|")
            for d in trims:
                w(f"| {d.label} | `{d.cusip}` | {d.shares_change:,} | ${d.value_change_usd_thousands/1000:,.2f}M | ${d.current.value_usd_millions:,.2f}M |")

    # ── 13F Limitations ──────────────────────────────────────────────────────
    w("---", "## 13F Limitations")
    w(
        "- Filings are published with a **45-day delay** and may not reflect current holdings.",
        "- 13F captures only U.S.-listed, Section 13(f)-reportable long securities. "
        "**Shorts, many international positions, cash, private equity, and most derivatives are excluded.**",
        "- Put/Call rows reflect reportable options exposure per Section 13(f) and do not describe "
        "complete option strategies, hedging programs, or notional exposure.",
        "- Intraperiod trading activity is not disclosed; positions reflect quarter-end snapshots only.",
        "- Cost basis and P&L are not disclosed.",
        "- Amendments (13F-HR/A) can revise prior conclusions; always verify amendment status.",
        "- CUSIP-to-ticker mapping carries uncertainty; confidence levels are labeled where applicable.",
    )

    # ── Scheduled Monitoring ─────────────────────────────────────────────────
    w("---", "## Quarterly Monitoring")
    w(
        f"Would you like quarterly updates for **{filing.filer_name}** after the 13F filing window? "
        "Default cadence: run once per quarter after the 45-day 13F deadline, verify the latest public filing "
        "at runtime, compare against the prior quarter unless requested otherwise."
    )

    # ── Disclaimer ───────────────────────────────────────────────────────────
    w("---", "## Disclaimer")
    w(f"> **Disclaimer.** {DISCLAIMER_TEXT}")

    # ── Branded Bottom Block ─────────────────────────────────────────────────
    w("---")
    w("![Wall Street Prompt](assets/wsp_logo.png)")
    w(REQUIRED_CTA)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Markdown saved → {output_path}")


# ── CSV ───────────────────────────────────────────────────────────────────────

def generate_csv(
    filing: FilingRecord,
    current: FilingData,
    output_path: pathlib.Path,
) -> None:
    """Export the full information table as a CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sorted_h = sorted(current.holdings, key=lambda h: h.value_usd_thousands, reverse=True)

    fieldnames = [
        "rank", "issuer_name", "ticker", "ticker_confidence",
        "cusip", "title_of_class", "value_usd_thousands", "value_usd_millions",
        "shares_or_principal", "share_type", "put_call",
        "investment_discretion", "other_manager",
        "voting_sole", "voting_shared", "voting_none",
        "pct_of_portfolio",
    ]
    total = current.total_value_usd_thousands

    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for rank, h in enumerate(sorted_h, 1):
            pct = h.value_usd_thousands / total * 100 if total else 0.0
            writer.writerow({
                "rank": rank,
                "issuer_name": h.issuer_name,
                "ticker": h.ticker,
                "ticker_confidence": h.ticker_confidence,
                "cusip": h.cusip,
                "title_of_class": h.title_of_class,
                "value_usd_thousands": h.value_usd_thousands,
                "value_usd_millions": round(h.value_usd_millions, 4),
                "shares_or_principal": h.shares_or_principal,
                "share_type": h.share_type,
                "put_call": h.put_call,
                "investment_discretion": h.investment_discretion,
                "other_manager": h.other_manager,
                "voting_sole": h.voting_sole,
                "voting_shared": h.voting_shared,
                "voting_none": h.voting_none,
                "pct_of_portfolio": round(pct, 4),
            })

    print(f"  CSV saved → {output_path}")


# ── All Three Outputs ─────────────────────────────────────────────────────────

def generate_all(
    filing: FilingRecord,
    current: FilingData,
    prior: Optional[FilingData],
    prior_filing: Optional[FilingRecord],
    output_dir: pathlib.Path,
) -> dict[str, pathlib.Path]:
    """Generate PDF, markdown memo, and CSV. Returns a dict of type → path."""
    slug = _slug(filing.filer_name)
    period = filing.period_of_report.replace("-", "")

    paths = {
        "pdf": output_dir / f"{slug}-{period}-holdings-report.pdf",
        "markdown": output_dir / f"{slug}-{period}-holdings-memo.md",
        "csv": output_dir / f"{slug}-{period}-holdings-table.csv",
    }

    print(f"\n  Generating reports for {filing.filer_name} ({filing.period_of_report}) …")
    generate_csv(filing, current, paths["csv"])
    generate_markdown(filing, current, prior, prior_filing, paths["markdown"])
    generate_pdf(filing, current, prior, prior_filing, paths["pdf"])

    return paths
