# Hedge Fund Holdings Tracker

Cursor Agent Skill + `cursort` CLI for institutional 13F holdings research with SEC EDGAR sourcing, WSP-branded PDF deliverables, and quarter-over-quarter comparison.

## Install

```bash
pip install -e .
```

## Generate a report (`cursort` CLI)

```bash
cursort --cik 0001067983 --compare --output output/berkshire
```

Options:

| Flag | Description |
|---|---|
| `--cik` | Manager CIK (e.g. `0001067983` for Berkshire) |
| `--name` | Search EDGAR by manager name |
| `--period` | Reporting period (`YYYY-MM-DD`) |
| `--compare` | QoQ comparison vs prior quarter |
| `--output` | Output directory (default: `./output`) |
| `--no-pdf` | Skip PDF; emit markdown + CSV only |

## Alternative: skill scripts

```bash
pip install -r requirements.txt
python3 .cursor/skills/hedge-fund-holdings-tracker/scripts/generate_report.py \
  --cik 0001067983 \
  --output-dir output/berkshire \
  --compare-prior
```

## Project layout

```
.cursor/skills/hedge-fund-holdings-tracker/
├── SKILL.md
├── assets/wsp_logo.png
├── references/          # methodology, design system, eval docs
└── scripts/             # agent-callable pipeline

src/                     # cursort Python package
tests/                   # unit tests
pyproject.toml           # pip install -e .
```

## Outputs

- `*.pdf` — canonical deliverable with 4 inline WSP-palette charts
- `*.md` — markdown memo with audit trail, limitations, disclaimer, and brand block
- `*.csv` — full information table export

## Research-only

This skill produces informational research from public filings. It does not provide investment advice, price targets, or allocation guidance.
