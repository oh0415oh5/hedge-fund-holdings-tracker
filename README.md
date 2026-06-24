# Hedge Fund Holdings Tracker

Cursor Agent Skill for institutional 13F holdings research with SEC EDGAR sourcing, WSP-branded PDF deliverables, and quarter-over-quarter comparison.

## Install

```bash
pip install -r requirements.txt
```

## Generate a report

```bash
python3 .cursor/skills/hedge-fund-holdings-tracker/scripts/generate_report.py \
  --cik 0001067983 \
  --output-dir output/berkshire \
  --compare-prior
```

Outputs:

- `*.pdf` — canonical deliverable with 4 inline WSP-palette charts
- `*.md` — markdown memo with audit trail, limitations, disclaimer, and brand block
- `*.csv` — full information table export

## Cursor skill layout

```
.cursor/skills/hedge-fund-holdings-tracker/
├── SKILL.md              # Agent instructions (auto-discovered by Cursor)
├── assets/wsp_logo.png   # Bundled brand asset
├── references/           # Methodology, design system, eval checklists
└── scripts/              # EDGAR fetch, parse, chart, and PDF pipeline
```

The root `SKILL.md` mirrors the Cursor skill for distribution outside `.cursor/skills/`.

## SEC EDGAR note

SEC requests a descriptive `User-Agent` header. Override with:

```bash
python3 .cursor/skills/hedge-fund-holdings-tracker/scripts/generate_report.py \
  --cik 0001067983 \
  --user-agent "YourName you@example.com"
```

## Research-only

This skill produces informational research from public filings. It does not provide investment advice, price targets, or allocation guidance.
