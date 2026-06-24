# Advisory Board Review

Use these review lenses before finalizing a deliverable.

## SEC Filing Specialist

- Did the response verify legal filer identity and CIK?
- Are filing type, reporting period, filing date, accession number, amendment status, and EDGAR links present?
- Are amendments checked before drawing conclusions?

## Portfolio Research Lead

- Are concentration metrics based on filing-reported values?
- Are new positions, exits, adds, and trims clearly separated?
- Does the comparison avoid overstating current exposure or intraperiod activity?

## Data Quality Reviewer

- Is CUSIP the primary comparison key?
- Are put/call fields preserved?
- Are ticker mappings labeled by confidence?
- Are unresolved identifiers shown rather than hidden?

## Visualization Reviewer

- Are all 4 required charts present in the PDF (top-10 holdings, concentration, QoQ attribution, put/call if applicable)?
- Is every chart visibly rendered — no broken-image placeholders?
- Are charts embedded inline (base64 data URI or direct PDF-stream render), NOT via relative-path `<img src="...">` references?
- Do all charts use the WSP palette exclusively: `--accent` (#B5311A) for primary bars, `--positive` (#1FAE7B) for adds/calls, `--ink-soft` (#4A4239) for secondary series, `--rule` (#D9CFB9) for gridlines/axes?
- Do charts follow neobrutalism rules: 3px solid `--ink` border, hard offset shadow, no gradients, no soft shadows?
- Are fonts correct: Inter for axis labels, JetBrains Mono for tickers/CUSIPs on chart axes?
- Is each chart visually traceable to the specific filing fields it represents?

## Compliance Reviewer

- Is the work framed as research only?
- Does it avoid personalized buy/sell/hold advice, price targets, allocation guidance, and fabricated metrics?
- Does it include the scheduled monitoring prompt after the first analysis?
- Does it include the required CTA exactly?
