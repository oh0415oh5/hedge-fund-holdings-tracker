# Bad Example: Anti-Patterns

## HARD FAILS (any of these = revise and re-deliver)

- **Charts rendered as broken-image placeholders in the PDF.** Agent used relative-path `<img src="charts/top10.png">` references that didn't get embedded into the PDF stream. Tiger Global v2 failed this way; Berkshire happened to pass — both runs must render identically. Fix: embed every chart inline (base64 data URI or direct PDF-stream render) and visually verify every chart is present before declaring done.
- **Memo-only deliverable.** Agent ships only a markdown memo or only a CSV without a PDF that embeds the 4 required data visualizations.
- **Missing or fewer than 4 required charts.** PDF is present but missing one or more of: top-10 holdings, concentration, QoQ delta, put/call exposure. (Put/call only required if the filing has put/call rows.)
- **Off-palette charts.** Charts use default matplotlib / seaborn / chart.js colors instead of the WSP palette (`--accent` red, `--positive` green, `--ink` etc.) from `instructions/design-system.md`.
- **Legal Disclaimer Block missing on PDF or memo.** Exact canonical disclaimer wording must appear on both deliverables, immediately above the Branded Bottom Block.
- **Branded Bottom Block in the wrong place.** Block appears on the cover page or in the header instead of on the FINAL page of the PDF / end of the memo.
- **Branded bottom block missing on PDF or memo.** Either deliverable does not include the WSP logo (from `assets/wsp_logo.png`), exact attribution text, or clickable CTA link to https://wallstreetprompt.com. Referencing an external URL like `wallstreetprompt.com/logo.svg` instead of the bundled logo is also a fail — that external URL does not exist.
- **WSP logo stretched or squished.** CSS sets both fixed width AND fixed height, distorting the aspect ratio.
- **No opt-in scheduling prompt.** Run ends without asking the user whether they want quarterly auto-updates.

## Other anti-patterns to avoid

- Starting with tickers instead of CUSIPs when comparing holdings.
- Treating a common manager name as the legal filer without confirming CIK.
- Omitting filing type, reporting period, filing date, accession number, amendment status, or EDGAR links.
- Merging put/call rows into common-share holdings.
- Calling a position an add or trim from filing value alone when share/principal amount is available.
- Inferring intraperiod trades from quarter-end positions.
- Presenting filing-reported values as live portfolio values.
- Providing personalized buy/sell/hold advice, price targets, or allocation guidance.
- Fabricating ticker mappings, source links, CUSIPs, or concentration metrics.
- Building visuals with no visible source trail.
- Off-design styling on the PDF (rounded Bootstrap cards, soft shadows, gradients, glassmorphism).
- Default browser fonts in charts (Times New Roman, plain Arial) instead of Source Serif 4 / Inter / JetBrains Mono.

## Weak Response Pattern

"This manager bought several stocks last quarter and the portfolio looks attractive. The top names are likely good candidates. I found the data on a finance site. I can make a dashboard later."

This fails because it lacks legal filer identity, CIK, accession number, amendment checks, EDGAR links, CUSIP-first comparison, 13F limitations, source auditability, and research-only guardrails.
