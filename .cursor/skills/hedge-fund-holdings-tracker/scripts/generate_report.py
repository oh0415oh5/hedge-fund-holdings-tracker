#!/usr/bin/env python3
"""Generate hedge fund 13F research deliverables (PDF, markdown, CSV)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from charts import build_chart_set
from compare_holdings import compare_snapshots
from edgar_client import EdgarClient
from parse_13f import parse_information_table
from report_builder import render_csv, render_markdown, render_pdf


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate WSP-styled 13F holdings research deliverables."
    )
    parser.add_argument("--cik", required=True, help="SEC CIK for the institutional manager")
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory for PDF, markdown memo, and CSV outputs",
    )
    parser.add_argument(
        "--compare-prior",
        action="store_true",
        help="Compare the latest filing against the immediately prior 13F quarter",
    )
    parser.add_argument(
        "--user-agent",
        default=None,
        help="SEC EDGAR User-Agent (name email@domain.com)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    client = EdgarClient(user_agent=args.user_agent) if args.user_agent else EdgarClient()
    filings = client.list_13f_filings(args.cik, limit=2 if args.compare_prior else 1)
    if not filings:
        print("No 13F filings found for CIK", args.cik, file=sys.stderr)
        return 1

    current_filing = filings[0]
    prior_filing = filings[1] if len(filings) > 1 else None

    current_xml = client.fetch_information_table_xml(current_filing)
    current_snapshot = parse_information_table(current_xml)

    comparison = None
    if args.compare_prior and prior_filing is not None:
        prior_xml = client.fetch_information_table_xml(prior_filing)
        prior_snapshot = parse_information_table(prior_xml)
        comparison = compare_snapshots(current_snapshot, prior_snapshot)
    else:
        prior_filing = None

    charts = build_chart_set(current_snapshot, comparison)
    logo_path = SKILL_DIR / "assets" / "wsp_logo.png"

    slug = current_filing.company_name.lower().replace(" ", "-")[:40]
    pdf_path = output_dir / f"{slug}-{current_filing.report_date}.pdf"
    memo_path = output_dir / f"{slug}-{current_filing.report_date}.md"
    csv_path = output_dir / f"{slug}-{current_filing.report_date}.csv"

    render_pdf(
        pdf_path,
        current_filing,
        current_snapshot,
        charts,
        logo_path,
        prior=prior_filing,
        comparison=comparison,
    )
    render_markdown(
        memo_path,
        current_filing,
        current_snapshot,
        prior=prior_filing,
        comparison=comparison,
    )
    render_csv(csv_path, current_snapshot)

    print(f"Wrote PDF: {pdf_path}")
    print(f"Wrote memo: {memo_path}")
    print(f"Wrote CSV: {csv_path}")
    print(
        "Would you like quarterly updates for this manager after the 13F filing window? "
        "Default cadence: run once per quarter after the 45-day 13F deadline."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
