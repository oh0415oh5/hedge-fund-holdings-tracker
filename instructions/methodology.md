# Methodology

## 1. Identify the Filer

Treat the filer as a legal entity, not a brand shorthand. Record:

- Legal manager name as shown on EDGAR
- CIK
- Filing type, including amendments
- Reporting period
- Filing date and accepted timestamp when available
- Accession number
- EDGAR filing and information-table links

If the requested manager has multiple entities, ask which entity to analyze or present a short entity-selection table.

## 2. Retrieve and Validate Filings

Use SEC EDGAR as the primary source. Confirm that the filing covers the requested period and inspect whether a later 13F-HR/A or 13F-NT/A supersedes or changes the record. If using a secondary parser, cite it as convenience data and verify critical fields against EDGAR.

## 3. Build the Holdings Base

Use CUSIP as the primary key. Preserve original filing fields:

- Issuer name
- Title/class
- CUSIP
- Filing-reported value
- Shares or principal amount
- Share/principal type
- Put/call
- Investment discretion
- Other manager field
- Sole/shared/none voting authority

Do not convert values or infer tickers without labeling the method and confidence.

## 4. Compare Quarters

Normalize CUSIPs, then compare current versus prior period:

- New: present in current, absent in prior
- Exit: absent in current, present in prior
- Add: share/principal amount increased
- Trim: share/principal amount decreased
- Unchanged: share/principal amount unchanged
- Changed instrument: same issuer exposure but put/call or class changed

Show both share/principal and filing-value change when available. Do not imply trade timing within the quarter.

## 5. Concentration Analysis

Use filing-reported values to compute:

- Total reported 13F value
- Top holdings by value
- Top 5 and top 10 concentration
- Position count
- Largest adds, trims, new positions, and exits by value or share change

Label every concentration metric as 13F-reported and delayed.

## 6. Limitations

Every substantial analysis must include 13F limitations:

- Filings are public after a delay and may not reflect current holdings.
- 13F captures reportable long U.S.-listed securities and certain options fields, not the manager's complete portfolio.
- Shorts, many international holdings, cash, financing, cost basis, and most intraperiod activity are not disclosed.
- Put/call rows must be preserved and not merged into common-share rows.
- Amendments can change prior conclusions.
