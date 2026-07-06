"""Render PDF and markdown deliverables with embedded charts."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from compare_holdings import ComparisonSummary
from edgar_client import FilingRef
from parse_13f import HoldingsSnapshot
from wsp_palette import ACCENT, INK, INK_SOFT, PAPER, RULE

LIMITATIONS = [
    "Filings are public after a 45-day delay and may not reflect current holdings.",
    "13F captures reportable long U.S.-listed securities and certain options fields, not the manager's complete portfolio.",
    "Shorts, many international holdings, cash, financing, cost basis, and most intraperiod activity are not disclosed.",
    "Put/call rows must be preserved and not merged into common-share rows.",
    "Amendments can change prior conclusions.",
    "CUSIP-to-ticker mapping may be uncertain when enrichment is applied.",
]

DISCLAIMER = (
    "This report is produced for informational and research purposes only. "
    "All holdings data is sourced from public SEC EDGAR 13F filings, which are reported "
    "with a 45-day delay and exclude shorts, hedges, cash, private holdings, derivatives "
    "detail, and intraperiod trading. This does not constitute investment advice. Past "
    "portfolio positioning is not indicative of future financial results. All trademarks "
    "are the property of their respective owners."
)

TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <style>
    @page { size: A4; margin: 18mm; }
    body {
      font-family: Inter, system-ui, sans-serif;
      color: {{ ink }};
      background: {{ paper }};
      font-size: 10.5pt;
      line-height: 1.45;
    }
    h1, h2 {
      font-family: "Source Serif 4", Georgia, serif;
      color: {{ ink }};
      margin-bottom: 8px;
    }
    .card {
      border: 3px solid {{ ink }};
      box-shadow: 6px 6px 0 0 {{ ink }};
      background: {{ paper }};
      padding: 16px;
      margin: 14px 0;
      border-radius: 2px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 9.5pt;
    }
    th, td {
      border: 1px solid {{ rule }};
      padding: 6px 8px;
      text-align: left;
      vertical-align: top;
    }
    th { background: #F1EADC; }
    .chart img {
      width: 100%;
      height: auto;
      display: block;
      border: 3px solid {{ ink }};
      box-shadow: 4px 4px 0 0 {{ ink }};
    }
    .disclaimer {
      border: 2px solid {{ rule }};
      padding: 14px;
      margin-top: 18px;
      font-size: 9pt;
      color: {{ ink_soft }};
    }
    .brand {
      border-top: 3px solid {{ ink }};
      padding-top: 18px;
      margin-top: 24px;
    }
    .brand img { height: 48px; width: auto; }
    .cta a { color: {{ accent }}; font-weight: 600; text-decoration: underline; }
    .muted { color: {{ ink_soft }}; font-size: 9pt; }
    .mono { font-family: "JetBrains Mono", monospace; font-size: 9pt; }
  </style>
</head>
<body>
  <h1>{{ title }}</h1>
  <p class="muted">Generated {{ generated_at }} UTC · Research-only institutional holdings snapshot</p>

  <div class="card">
    <h2>Executive Research Snapshot</h2>
    <p>{{ executive_summary }}</p>
  </div>

  <div class="card">
    <h2>Filer and Filing Audit Trail</h2>
    <table>
      <tbody>
        {% for label, value in audit_rows %}
        <tr><th>{{ label }}</th><td class="mono">{{ value }}</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <div class="card chart"><h2>Top-10 Holdings</h2><img src="data:image/png;base64,{{ charts.top10 }}" alt="Top 10 holdings chart" /></div>
  <div class="card chart"><h2>Portfolio Concentration</h2><img src="data:image/png;base64,{{ charts.concentration }}" alt="Concentration chart" /></div>
  {% if charts.qoq %}
  <div class="card chart"><h2>QoQ Change Attribution</h2><img src="data:image/png;base64,{{ charts.qoq }}" alt="QoQ chart" /></div>
  {% endif %}
  {% if charts.put_call %}
  <div class="card chart"><h2>Put/Call Exposure</h2><img src="data:image/png;base64,{{ charts.put_call }}" alt="Put call chart" /></div>
  {% endif %}

  <div class="card">
    <h2>13F Limitations</h2>
    <ul>
      {% for item in limitations %}<li>{{ item }}</li>{% endfor %}
    </ul>
  </div>

  <div class="disclaimer">
    <strong>Disclaimer.</strong> {{ disclaimer }}
  </div>

  <div class="brand">
    <img src="data:image/png;base64,{{ logo_b64 }}" alt="Wall Street Prompt" />
    <p>This skill was engineered by Wall Street Prompt</p>
    <p class="cta"><a href="https://wallstreetprompt.com">Learn how to use AI for investing →</a></p>
  </div>
</body>
</html>
"""


def _logo_base64(logo_path: Path) -> str:
    return base64.b64encode(logo_path.read_bytes()).decode("ascii")


def _audit_rows(filing: FilingRef, prior: FilingRef | None) -> list[tuple[str, str]]:
    rows = [
        ("Legal filer", filing.company_name),
        ("CIK", filing.cik),
        ("Filing type", filing.filing_type),
        ("Reporting period", filing.report_date),
        ("Filing date", filing.filing_date),
        ("Accession number", filing.accession_number),
        ("Amendment status", "Amendment" if filing.is_amendment else "Original filing"),
        ("EDGAR filing link", filing.edgar_filing_url),
        ("EDGAR index link", filing.edgar_index_url),
    ]
    if prior is not None:
        rows.extend(
            [
                ("Prior reporting period", prior.report_date),
                ("Prior accession number", prior.accession_number),
            ]
        )
    return rows


def _executive_summary(
    filing: FilingRef,
    current: HoldingsSnapshot,
    comparison: ComparisonSummary | None,
) -> str:
    top = current.top_by_value(1)
    lead = top[0].issuer_name if top else "N/A"
    base = (
        f"{filing.company_name} reported {len(current.holdings)} 13F positions for "
        f"{filing.report_date} with filing-reported value of "
        f"${current.total_reported_value:,}. The largest position by reported value is {lead}."
    )
    if comparison is None:
        return base
    return (
        f"{base} Quarter-over-quarter comparison shows {len(comparison.new_positions)} new "
        f"positions, {len(comparison.exits)} exits, {len(comparison.adds)} adds, and "
        f"{len(comparison.trims)} trims using CUSIP-first matching."
    )


def render_pdf(
    output_path: Path,
    filing: FilingRef,
    current: HoldingsSnapshot,
    charts: dict[str, str],
    logo_path: Path,
    prior: FilingRef | None = None,
    comparison: ComparisonSummary | None = None,
) -> None:
    env = Environment(autoescape=select_autoescape(["html"]))
    html = env.from_string(TEMPLATE).render(
        title=f"{filing.company_name} — 13F Holdings Snapshot",
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        executive_summary=_executive_summary(filing, current, comparison),
        audit_rows=_audit_rows(filing, prior),
        charts=charts,
        limitations=LIMITATIONS,
        disclaimer=DISCLAIMER,
        logo_b64=_logo_base64(logo_path),
        ink=INK,
        ink_soft=INK_SOFT,
        paper=PAPER,
        rule=RULE,
        accent=ACCENT,
    )
    HTML(string=html, base_url=str(output_path.parent)).write_pdf(str(output_path))


def render_markdown(
    output_path: Path,
    filing: FilingRef,
    current: HoldingsSnapshot,
    prior: FilingRef | None = None,
    comparison: ComparisonSummary | None = None,
) -> None:
    lines = [
        f"# {filing.company_name} — 13F Holdings Snapshot",
        "",
        "## Executive Research Snapshot",
        _executive_summary(filing, current, comparison),
        "",
        "## Filer and Filing Audit Trail",
        "",
        "| Field | Value |",
        "|---|---|",
    ]
    for label, value in _audit_rows(filing, prior):
        lines.append(f"| {label} | {value} |")

    lines.extend(["", "## 13F Limitations", ""])
    for item in LIMITATIONS:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "> **Disclaimer.** " + DISCLAIMER,
            "",
            "![Wall Street Prompt](assets/wsp_logo.png)",
            "",
            "This skill was engineered by Wall Street Prompt",
            "",
            "Learn how to use AI for investing → [wallstreetprompt.com](https://wallstreetprompt.com)",
            "",
            "Would you like quarterly updates for this manager after the 13F filing window? "
            "Default cadence: run once per quarter after the 45-day 13F deadline, verify latest "
            "public filing at runtime, compare against prior quarter unless requested otherwise.",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def render_csv(output_path: Path, snapshot: HoldingsSnapshot) -> None:
    headers = [
        "issuer_name",
        "title_of_class",
        "cusip",
        "value_usd",
        "shares_or_principal",
        "share_or_principal_type",
        "put_call",
        "investment_discretion",
        "other_manager",
        "voting_sole",
        "voting_shared",
        "voting_none",
        "ticker",
        "mapping_confidence",
    ]
    lines = [",".join(headers)]
    for holding in snapshot.holdings:
        row = [
            holding.issuer_name,
            holding.title_of_class,
            holding.cusip,
            str(holding.value_usd),
            str(holding.shares_or_principal),
            holding.share_or_principal_type,
            holding.put_call,
            holding.investment_discretion,
            holding.other_manager,
            str(holding.voting_sole),
            str(holding.voting_shared),
            str(holding.voting_none),
            holding.ticker or "",
            holding.mapping_confidence,
        ]
        escaped = [f'"{value.replace(chr(34), chr(34)*2)}"' for value in row]
        lines.append(",".join(escaped))
    output_path.write_text("\n".join(lines), encoding="utf-8")
