"""
CLI entry point for the Hedge Fund Holdings Tracker skill.

Usage examples:
  python -m src.cli --cik 0001067983               # Berkshire — latest 13F
  python -m src.cli --cik 0001067983 --compare     # Berkshire with QoQ comparison
  python -m src.cli --name "Berkshire" --compare   # search by name
  python -m src.cli --cik 0001067983 --period 2024-09-30  # specific period
"""

from __future__ import annotations

import argparse
import pathlib
import sys

from .edgar import (
    _pad_cik,
    get_filer_by_cik,
    get_13f_filings,
    download_info_table,
)
from .parser import parse_info_table
from .report import generate_all


def _find_cik_by_name(name: str) -> str:
    """Search EDGAR for a manager name and return a CIK interactively."""
    import urllib.parse
    import requests

    headers = {
        "User-Agent": "WallStreetPrompt research@wallstreetprompt.com",
        "Accept": "application/json",
    }
    url = (
        f"https://efts.sec.gov/LATEST/search-index"
        f"?q=%22{urllib.parse.quote(name)}%22&forms=13F-HR"
    )
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        hits = resp.json().get("hits", {}).get("hits", [])
        seen: dict[str, str] = {}
        for hit in hits[:20]:
            src = hit.get("_source", {})
            entity = src.get("entity_name") or ""
            cik_raw = src.get("file_num") or src.get("cik") or ""
            cik_clean = "".join(c for c in str(cik_raw) if c.isdigit())
            if cik_clean and entity and cik_clean not in seen:
                seen[cik_clean] = entity
        if seen:
            print(f"\nFound {len(seen)} candidate(s) for '{name}':\n")
            items = list(seen.items())
            for i, (cik, en) in enumerate(items, 1):
                print(f"  [{i}] {en}  (CIK: {cik})")
            choice = input("\nEnter number (or CIK directly): ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(items):
                return items[int(choice) - 1][0]
            # treat as raw CIK
            return choice
    except Exception as exc:
        print(f"  Search failed: {exc}", file=sys.stderr)

    return input(f"Enter CIK for '{name}': ").strip()


def main(args: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Hedge Fund Holdings Tracker — 13F analysis & PDF report generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--cik", help="Manager CIK (can include leading zeros)")
    parser.add_argument("--name", help="Manager name to search on EDGAR")
    parser.add_argument(
        "--period",
        help="Reporting period (YYYY-MM-DD). Defaults to the most recent filing.",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare current period against the prior quarter.",
    )
    parser.add_argument(
        "--output",
        default="output",
        help="Output directory (default: ./output)",
    )
    parser.add_argument(
        "--no-pdf",
        action="store_true",
        help="Skip PDF generation (faster, produces markdown + CSV only).",
    )

    ns = parser.parse_args(args)

    # ── Resolve CIK ──────────────────────────────────────────────────────────
    cik = ns.cik
    if not cik and ns.name:
        cik = _find_cik_by_name(ns.name)
    if not cik:
        parser.error("Provide --cik or --name.")

    cik = _pad_cik(cik)
    print(f"\n[1/4] Fetching filer info for CIK {cik} …")
    filer = get_filer_by_cik(cik)
    print(f"      Filer: {filer.name}")

    # ── Discover filings ──────────────────────────────────────────────────────
    print(f"[2/4] Fetching 13F filing list …")
    filings = get_13f_filings(cik, max_filings=20)
    if not filings:
        print(f"  ERROR: No 13F-HR filings found for CIK {cik}.", file=sys.stderr)
        sys.exit(1)

    print(f"      Found {len(filings)} filing(s).")
    for f in filings[:5]:
        print(f"        • {f.form_type}  period={f.period_of_report}  filed={f.filed_date}  acc={f.accession_number}")

    # Select target filing
    if ns.period:
        matches = [f for f in filings if f.period_of_report == ns.period]
        if not matches:
            print(f"  WARNING: No filing found for period {ns.period}; using most recent.", file=sys.stderr)
            target = filings[0]
        else:
            # Prefer amendment if available
            amendments = [f for f in matches if f.is_amendment]
            target = amendments[-1] if amendments else matches[0]
    else:
        # Use most recent filing; if there's an amendment for the same period, prefer it
        target = filings[0]
        same_period = [f for f in filings if f.period_of_report == target.period_of_report]
        amendments = [f for f in same_period if f.is_amendment]
        if amendments:
            target = amendments[-1]
            print(f"      Using amendment: {target.accession_number}")

    prior_filing = None
    if ns.compare and len(filings) > 1:
        # Find the prior period filing (different period_of_report)
        current_period = target.period_of_report
        prior_candidates = [f for f in filings if f.period_of_report != current_period]
        if prior_candidates:
            prior_filing = prior_candidates[0]
            same_prior = [f for f in prior_candidates if f.period_of_report == prior_filing.period_of_report]
            amendments_prior = [f for f in same_prior if f.is_amendment]
            if amendments_prior:
                prior_filing = amendments_prior[-1]
            print(f"      Prior period: {prior_filing.period_of_report} ({prior_filing.accession_number})")

    # ── Download & parse information tables ──────────────────────────────────
    print(f"[3/4] Downloading information table for {target.period_of_report} …")
    raw_current = download_info_table(target)
    current_data = parse_info_table(raw_current)
    print(f"      Parsed {current_data.holding_count} holdings  "
          f"(total: ${current_data.total_value_usd_millions:,.1f}M)")

    prior_data = None
    if prior_filing:
        print(f"      Downloading prior information table for {prior_filing.period_of_report} …")
        raw_prior = download_info_table(prior_filing)
        prior_data = parse_info_table(raw_prior)
        print(f"      Parsed {prior_data.holding_count} prior holdings  "
              f"(total: ${prior_data.total_value_usd_millions:,.1f}M)")

    # ── Generate reports ──────────────────────────────────────────────────────
    print(f"[4/4] Generating reports …")
    output_dir = pathlib.Path(ns.output)

    if ns.no_pdf:
        from .report import generate_csv, generate_markdown, _slug
        import re
        slug = re.sub(r"[^a-z0-9]+", "-", target.filer_name.lower()).strip("-")
        period = target.period_of_report.replace("-", "")
        csv_path = output_dir / f"{slug}-{period}-holdings-table.csv"
        md_path = output_dir / f"{slug}-{period}-holdings-memo.md"
        generate_csv(target, current_data, csv_path)
        generate_markdown(target, current_data, prior_data, prior_filing, md_path)
        paths = {"csv": csv_path, "markdown": md_path}
    else:
        paths = generate_all(target, current_data, prior_data, prior_filing, output_dir)

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print(f"  Manager          : {target.filer_name}")
    print(f"  CIK              : {target.cik}")
    print(f"  Filing type      : {target.form_type}")
    print(f"  Reporting period : {target.period_of_report}")
    print(f"  Filed            : {target.filed_date}")
    print(f"  Accession        : {target.accession_number}")
    print(f"  Amendment status : {'Amendment' if target.is_amendment else 'Original'}")
    print(f"  Total 13F value  : ${current_data.total_value_usd_millions:,.1f}M")
    print(f"  Positions        : {current_data.holding_count:,}")
    print(f"  Has Put/Call     : {'Yes' if current_data.has_put_call else 'No'}")
    print(f"\n  Output files:")
    for kind, path in paths.items():
        print(f"    {kind.upper():10s}: {path}")
    print(f"{'─'*60}")
    print(
        "\n  Would you like quarterly updates for this manager after the 13F filing window?\n"
        "  Run once per quarter after the 45-day 13F deadline, verify the latest public filing\n"
        "  at runtime, and compare against the prior quarter unless requested otherwise.\n"
    )


if __name__ == "__main__":
    main()
