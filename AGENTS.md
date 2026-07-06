# AGENTS.md

## Cursor Cloud specific instructions

### What this repo is
This is an **Agent Skill**, not a runnable application. It contains only markdown
instructions (`SKILL.md`, `instructions/`, `examples/`, `eval/`) plus one bundled
asset (`assets/wsp_logo.png`). There is **no source code, no package manifest, no
tests, no build step, and no server**. "Linting/testing/building" in the
traditional sense does not apply — the only meaningful way to exercise this skill
is to *execute its workflow*: fetch a 13F from SEC EDGAR, parse it, render the 4
required WSP-palette charts, and produce a PDF + markdown memo + CSV.

### Proven execution toolchain
The update script installs `matplotlib` + `requests` (numpy comes along). PDF
generation uses the **pre-installed `google-chrome`** in headless mode
(`--print-to-pdf`) rendering HTML/CSS — this faithfully reproduces the
neobrutalism design system (thick borders, hard offset shadows, exact palette)
**without** WeasyPrint/Cairo/Pango system dependencies. Do not add WeasyPrint;
prefer the matplotlib-charts → base64-inline → HTML → headless-Chrome → PDF path
(this is one of the embedding methods endorsed in `instructions/output-structure.md`).

### Non-obvious gotchas (learned during setup)
- **SEC EDGAR requires a descriptive `User-Agent` header** (e.g.
  `"<app> <contact-email>"`), otherwise requests are rejected. Endpoints used:
  `https://data.sec.gov/submissions/CIK##########.json` for filing discovery and
  `https://www.sec.gov/Archives/edgar/data/<cik>/<accession-no-dashes>/index.json`
  to locate the information-table XML (the `.xml` file that is *not*
  `primary_doc.xml`).
- **Post-2023 13F `value` fields are whole US dollars**, not thousands. Divide by
  1e6 for "USD millions".
- **Holdings are split across multiple `otherManager` rows.** Aggregate by
  `(cusip, putCall)` before ranking/concentration, or top holdings will be wrong
  (e.g. Berkshire's Apple position spans several rows).
- **Keep put/call rows separate** from common-stock rows; only render the put/call
  chart if the filing actually contains put/call rows.
- **Headless Chrome PDF caveat:** `--print-to-pdf` writes the file but the Chrome
  process often does **not** exit cleanly, so a blocking `subprocess.run` hangs.
  Bound it with a timeout, then verify the output file exists/non-trivial size and
  kill the process. Always pass a unique `--user-data-dir=$(mktemp -d)` — reusing
  the default profile causes `SingletonLock` collisions that abort the run and
  leave many lingering `chrome` processes (which then break subsequent shell
  spawns). If shells start failing to spawn, kill leftover chrome by PID.
- **pip on this Ubuntu 24.04 system Python** needs `--break-system-packages`
  (PEP 668), matching how `requests`/`numpy` are already in system site-packages.

### Output / scope
No live website is required (confirmed in `SKILL.md`). The canonical deliverable
is a PDF with 4 embedded charts plus a markdown memo and a CSV; generate these to
a scratch/output directory rather than committing them into this skill repo.
