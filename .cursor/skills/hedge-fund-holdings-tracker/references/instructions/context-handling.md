# Context Handling

## Inputs to Capture

Capture the user's target manager, period, comparison baseline, desired depth, and preferred format. If missing, default to the latest public 13F-HR or amendment for the manager and compare to the immediately prior quarter when comparison is requested.

## Identity Resolution

Resolve manager names through EDGAR legal names and CIKs. If a common name maps to multiple filers, pause for disambiguation or provide a compact choice list with CIKs and recent filing dates.

## Source Hierarchy

1. SEC EDGAR filing page and information table
2. SEC submissions/companyfacts metadata where useful for filing discovery
3. Manager website only for identity support, never as a substitute for filing data
4. Secondary datasets only for convenience parsing or ticker enrichment

## Data Handling Rules

- Compare holdings CUSIP-first.
- Keep put/call rows separate from common-share rows.
- Preserve filing-reported values before adding optional enrichments.
- Mark ticker mappings as high, medium, low, or unresolved.
- Keep amendment status visible in the final audit trail.
- Never fill missing fields with invented values.

## Scheduled Monitoring Context

After the first delivered analysis, ask:

Would you like quarterly updates for this manager after the 13F filing window?

If accepted, use the default schedule: run once per quarter after the 45-day 13F deadline, verify latest public filing at runtime, compare against prior quarter unless requested otherwise.

Store or pass along manager name, CIK, filing type, output preference, comparison baseline, and any requested visuals. Do not assume future filing availability.
