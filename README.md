# cursort — Hedge Fund Holdings Tracker

**cursort** is a CLI tool that fetches SEC EDGAR 13F filings for any institutional manager and produces a research-grade PDF report, a markdown memo, and a CSV holdings table — all styled with the Wall Street Prompt design system.

## Quick start

```bash
pip install -e .          # install from source (requires Python ≥ 3.10)
cursort --help
```

## Usage

```
cursort [--cik CIK | --name NAME] [--period YYYY-MM-DD] [--compare] [--output DIR]
```

| Flag | Description |
|---|---|
| `--cik` | Manager CIK (e.g. `0001067983` for Berkshire Hathaway) |
| `--name` | Manager name to search on EDGAR (interactive CIK selector) |
| `--compare` | Include quarter-over-quarter change analysis vs. the prior filing |
| `--period` | Target reporting period `YYYY-MM-DD` (defaults to the latest filing) |
| `--output` | Output directory (default: `./output`) |
| `--no-pdf` | Skip PDF generation; produce markdown + CSV only |

### Examples

```bash
# Berkshire Hathaway — latest 13F with QoQ comparison
cursort --cik 0001067983 --compare

# Search by name (interactive CIK selection)
cursort --name "Tiger Global" --compare

# Specific period, no PDF
cursort --cik 0001911216 --period 2024-09-30 --no-pdf
```

## Output

Each run produces three files in `<output>/`:

| File | Contents |
|---|---|
| `<slug>-<period>-holdings-report.pdf` | PDF with 4 embedded WSP-palette charts + full tables |
| `<slug>-<period>-holdings-memo.md` | Markdown research memo |
| `<slug>-<period>-holdings-table.csv` | Full information table (one row per CUSIP) |

### Required charts (always embedded in the PDF)

1. **Top-10 Holdings** — horizontal bar, filing-reported value in USD millions
2. **Portfolio Concentration** — donut: top-5 / top-6–10 / top-11–25 / rest
3. **QoQ Change Attribution** — grouped bar: new positions, exits, adds, trims (count + USD value)
4. **Put/Call Exposure** — horizontal bar per issuer (only rendered when the filing has put/call rows)

## Design system

All outputs use the [Wall Street Prompt](https://wallstreetprompt.com) neobrutalism design system:

- Palette: `#FAF6EE` paper · `#1F1B16` ink · `#B5311A` accent · `#1FAE7B` positive
- Fonts: Inter (body), JetBrains Mono (tickers / CUSIPs)
- Cards: 3 px solid `--ink` border, 6 px hard-offset shadow, no gradients or rounded corners

## Skill compliance

This tool implements the `hedge-fund-holdings-tracker` Cursor skill spec (`SKILL.md`):

- CUSIP-first QoQ comparison
- EDGAR audit trail on every deliverable (CIK, accession, period, date, amendment status)
- 13F limitations stated clearly
- Legal disclaimer block with exact canonical wording
- Branded bottom block with WSP logo, attribution, and CTA
- Opt-in quarterly scheduling prompt

## Data sources

All data is sourced from [SEC EDGAR](https://www.sec.gov/cgi-bin/browse-edgar) public filings only.
This tool does not provide investment advice.

---

*This skill was engineered by Wall Street Prompt. Learn how to use AI for investing at [wallstreetprompt.com](https://wallstreetprompt.com).*
