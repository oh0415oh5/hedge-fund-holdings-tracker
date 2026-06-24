# Evaluation Checklist

## Must Pass (HARD-FAIL conditions)

- [ ] **HARD FAIL** — PDF deliverable produced with all 4 required data visualizations: top-10 holdings (horizontal bar), portfolio concentration (donut or stacked bar), QoQ change attribution (grouped bar), and put/call exposure (if filing has put/call rows). Markdown-only memo without PDF = fail.
- [ ] **HARD FAIL** — Every required chart in the PDF is visibly rendered. NO broken-image placeholders. Confirmed by opening the PDF before declaring done. Tiger Global parity with Berkshire is the bar.
- [ ] **HARD FAIL** — Charts embedded inline (base64 data URI or direct render into the PDF stream), NOT relative-path `<img src="charts/...">` references that can break.
- [ ] **HARD FAIL** — All charts use WSP palette and neobrutalism conventions per `instructions/design-system.md`. Default matplotlib / seaborn / chart.js colors = fail.
- [ ] **HARD FAIL** — Legal Disclaimer Block visibly rendered on PDF AND markdown memo with the exact canonical wording from `instructions/output-structure.md` (informational/research only, EDGAR 13F caveat with 45-day delay + excluded items, not investment advice, past performance not indicative, trademarks belong to owners).
- [ ] **HARD FAIL** — Branded Bottom Block is on the FINAL page of the PDF (not the cover) AND at the end of the markdown memo, after the Disclaimer. NOT in the header. NOT in a top-left chip.
- [ ] **HARD FAIL** — Branded bottom block present and complete: WSP logo image rendered from `assets/wsp_logo.png`, exact attribution text "This skill was engineered by Wall Street Prompt", clickable CTA link "Learn how to use AI for investing →" pointing to https://wallstreetprompt.com.
- [ ] **HARD FAIL** — Logo references the bundled `assets/wsp_logo.png`, not an external URL like `wallstreetprompt.com/logo.svg` (which does not exist).
- [ ] **HARD FAIL** — WSP logo aspect ratio preserved on PDF and memo (not stretched or squished). CSS sets only height OR only width, not both.
- [ ] **HARD FAIL** — EDGAR audit trail present in PDF and memo: CIK, accession number, reporting period, filing date, EDGAR filing link, amendment status.
- [ ] **HARD FAIL** — 13F limitations stated clearly: 45-day lag, Section 13(f) scope only, no shorts/hedges/cash/private, partial portfolio nature, put/call flags do not describe complete option strategy, amendments possible, CUSIP-to-ticker mapping uncertainty.
- [ ] **HARD FAIL** — Agent asks user about opt-in quarterly scheduling at end of run.

## Must Pass (other criteria)

- Frontmatter name is `hedge-fund-holdings-tracker`.
- Description triggers on hedge fund holdings, institutional manager 13F, SEC EDGAR, filing comparisons, CUSIP holdings, new positions/exits/adds/trims, portfolio concentration, and quarterly monitoring.
- The response is positioned for sophisticated research users or portfolio managers.
- Legal filer identity and CIK are verified before conclusions.
- Holdings comparison is CUSIP-first.
- Put/call rows are preserved verbatim where they appear in the filing.
- Mapping confidence is visible for ticker or issuer enrichment; tickers left "not mapped" if confidence is low.
- New positions, exits, adds, and trims are defined from current versus prior filing data.
- Research-only guardrails block personalized buy/sell/hold advice, price targets, allocation guidance, and fabricated metrics.
- Sources are sufficient for audit.

## Pre-Delivery Chart Verification (COMPLETE BEFORE DECLARING DONE)

Run through each step in order before delivering the PDF:

1. Open the rendered PDF and inspect every page.
2. Confirm chart 1 (Top-10 Holdings horizontal bar) is visibly rendered — bars in `--accent` (#B5311A), issuer names in JetBrains Mono on Y-axis.
3. Confirm chart 2 (Portfolio Concentration stacked bar or donut) is visibly rendered — top 5 in `--accent`, top 10 in `--ink-soft`, top 25 in `--ink-mute`, remainder in `--rule`.
4. Confirm chart 3 (QoQ Change Attribution grouped bar) is visibly rendered — new positions and adds in `--positive` (#1FAE7B), exits and trims in `--accent`.
5. Confirm chart 4 (Put/Call Exposure) is visibly rendered IF the filing contains put/call rows. If no put/call rows exist, document that explicitly.
6. If any chart shows a broken-image placeholder, stop — regenerate the PDF using base64 data URI embedding or direct PDF-stream rendering. Do NOT deliver a PDF with broken charts.
7. Confirm the Legal Disclaimer Block appears above the Branded Bottom Block on the final page of the PDF.
8. Confirm the Branded Bottom Block is on the FINAL page of the PDF (not the cover, not a header).
9. Confirm the WSP logo renders at natural aspect ratio (height set only, width auto).

## Advisory Board Final-Pass (recommended before delivery)

Run each lens from `eval/advisory-board.md` before declaring the run complete:

- [ ] SEC Filing Specialist: filer identity, CIK, accession number, amendment check, EDGAR links present?
- [ ] Portfolio Research Lead: concentration metrics from filing-reported values; new/exit/add/trim clearly separated?
- [ ] Data Quality Reviewer: CUSIP-first comparison; put/call fields preserved; ticker mapping confidence labeled?
- [ ] Visualization Reviewer: all 4 required charts present, inline-embedded, WSP palette, neobrutalism styling?
- [ ] Compliance Reviewer: research-only framing; no advice/targets; scheduling prompt included; CTA exact?

## V4 QA Fail Rules

Fail the output if ANY of the following are present:

- Markdown-only memo or CSV-only output without a PDF that embeds the 4 required charts.
- Fewer than 4 required charts in the PDF (put/call only required if filing has put/call rows).
- Off-palette charts (default matplotlib / seaborn / chart.js colors instead of WSP palette).
- Branded bottom block missing or incomplete on EITHER the PDF or the memo.
- Logo referenced from an external URL instead of the bundled `assets/wsp_logo.png`.
- Off-design styling (rounded Bootstrap cards, soft shadows, gradients, glassmorphism, off-palette colors).
- Opt-in scheduling prompt missing at end of run.
- Audit trail gaps for filer identity, CIK, filing period, filing date, accession number, amendment status, or EDGAR links.
- CUSIP-first comparison skipped without a documented reason.
- Put/call information dropped or merged incorrectly.
- The answer includes personalized advice, price targets, allocation guidance, or fabricated metrics.
- Audience wording is inconsistent with a premium investor research workflow for sophisticated users.
