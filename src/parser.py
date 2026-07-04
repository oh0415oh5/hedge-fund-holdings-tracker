"""Parse SEC 13F information table XML/HTML into structured holding records."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from lxml import etree
from bs4 import BeautifulSoup


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class Holding:
    issuer_name: str
    title_of_class: str
    cusip: str
    value_usd_thousands: int          # as reported (thousands)
    shares_or_principal: int
    share_type: str                   # "SH" or "PRN"
    put_call: str                     # "Put", "Call", or ""
    investment_discretion: str
    other_manager: str
    voting_sole: int
    voting_shared: int
    voting_none: int

    # Enrichment (populated later)
    ticker: str = ""
    ticker_confidence: str = ""       # "high", "medium", "low", "unresolved"

    @property
    def value_usd(self) -> float:
        """Return value in full USD (multiply thousands × 1000)."""
        return self.value_usd_thousands * 1000

    @property
    def value_usd_millions(self) -> float:
        return self.value_usd_thousands / 1000.0

    @property
    def label(self) -> str:
        """Display label: issuer name + ticker if available."""
        if self.ticker and self.ticker_confidence in ("high", "medium"):
            return f"{self.issuer_name} ({self.ticker})"
        return self.issuer_name


@dataclass
class FilingData:
    holdings: list[Holding] = field(default_factory=list)
    total_value_usd_thousands: int = 0
    holding_count: int = 0
    has_put_call: bool = False

    def compute_totals(self) -> None:
        self.total_value_usd_thousands = sum(h.value_usd_thousands for h in self.holdings)
        self.holding_count = len(self.holdings)
        self.has_put_call = any(h.put_call for h in self.holdings)

    @property
    def total_value_usd_millions(self) -> float:
        return self.total_value_usd_thousands / 1000.0


# ── Parser ────────────────────────────────────────────────────────────────────

# Known XML namespaces used in 13F filings
_NS_PATTERNS = [
    r"\{.*?informationTable.*?\}",
    r"\{.*?13F.*?\}",
]


def _strip_ns(tag: str) -> str:
    """Remove XML namespace from a tag name."""
    return re.sub(r"^\{[^}]*\}", "", tag)


def parse_info_table(raw: str) -> FilingData:
    """
    Parse a 13F information table from raw XML or HTML text.
    Returns a FilingData object with all holdings.
    """
    raw_stripped = raw.strip()
    if raw_stripped.startswith("<") and ("<?xml" in raw_stripped[:100] or "<informationTable" in raw_stripped[:500] or "<ns1:" in raw_stripped[:500]):
        try:
            return _parse_xml(raw_stripped)
        except Exception:
            pass
    # HTML fallback
    return _parse_html(raw_stripped)


def _parse_xml(raw: str) -> FilingData:
    """Parse the standard 13F XML information table."""
    # lxml needs bytes for encoding declarations
    raw_bytes = raw.encode("utf-8") if isinstance(raw, str) else raw
    root = etree.fromstring(raw_bytes)

    holdings: list[Holding] = []

    # The root may be <informationTable> or wrapped in another element
    # Find all <infoTable> descendants regardless of namespace
    info_tables = root.findall(".//{*}infoTable")
    if not info_tables:
        info_tables = root.findall(".//{*}InfoTable")
    if not info_tables:
        # Try without namespace wildcard (older files)
        info_tables = root.findall(".//infoTable")

    for entry in info_tables:
        def txt(tag: str) -> str:
            el = entry.find(f"{{*}}{tag}")
            if el is None:
                el = entry.find(tag)
            if el is None:
                # case-insensitive walk
                for child in entry.iter():
                    if _strip_ns(child.tag).lower() == tag.lower():
                        return (child.text or "").strip()
                return ""
            return (el.text or "").strip()

        def child_txt(parent_tag: str, child_tag: str) -> str:
            parent = entry.find(f"{{*}}{parent_tag}")
            if parent is None:
                parent = entry.find(parent_tag)
            if parent is None:
                for child in entry.iter():
                    if _strip_ns(child.tag).lower() == parent_tag.lower():
                        parent = child
                        break
            if parent is None:
                return ""
            el = parent.find(f"{{*}}{child_tag}")
            if el is None:
                el = parent.find(child_tag)
            if el is None:
                for child in parent.iter():
                    if _strip_ns(child.tag).lower() == child_tag.lower():
                        return (child.text or "").strip()
                return ""
            return (el.text or "").strip()

        try:
            holdings.append(Holding(
                issuer_name=txt("nameOfIssuer") or txt("issuerName"),
                title_of_class=txt("titleOfClass"),
                cusip=txt("cusip"),
                value_usd_thousands=_int(txt("value")),
                shares_or_principal=_int(
                    child_txt("shrsOrPrnAmt", "sshPrnamt") or txt("sshPrnamt")
                ),
                share_type=child_txt("shrsOrPrnAmt", "sshPrnamtType") or txt("sshPrnamtType") or "SH",
                put_call=txt("putCall"),
                investment_discretion=txt("investmentDiscretion"),
                other_manager=txt("otherManager"),
                voting_sole=_int(child_txt("votingAuthority", "Sole") or txt("Sole")),
                voting_shared=_int(child_txt("votingAuthority", "Shared") or txt("Shared")),
                voting_none=_int(child_txt("votingAuthority", "None") or txt("None")),
            ))
        except Exception:
            continue

    data = FilingData(holdings=holdings)
    data.compute_totals()
    return data


def _parse_html(raw: str) -> FilingData:
    """Fallback HTML parser for 13F tables (some older filings are HTML)."""
    soup = BeautifulSoup(raw, "lxml")
    holdings: list[Holding] = []

    # Look for tables — typically the information table has many rows
    tables = soup.find_all("table")
    best = None
    best_rows = 0
    for table in tables:
        rows = table.find_all("tr")
        if len(rows) > best_rows:
            best_rows = len(rows)
            best = table

    if best is None or best_rows < 2:
        return FilingData()

    rows = best.find_all("tr")
    # Try to detect header row
    header_idx = 0
    header_cells = [c.get_text(strip=True).lower() for c in rows[0].find_all(["th", "td"])]
    col_map = _map_html_columns(header_cells)

    for row in rows[1:]:
        cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
        if len(cells) < 5:
            continue
        try:
            def gc(key: str, default: str = "") -> str:
                idx = col_map.get(key)
                if idx is not None and idx < len(cells):
                    return cells[idx]
                return default

            holdings.append(Holding(
                issuer_name=gc("name"),
                title_of_class=gc("class"),
                cusip=gc("cusip"),
                value_usd_thousands=_int(gc("value").replace(",", "")),
                shares_or_principal=_int(gc("shares").replace(",", "")),
                share_type=gc("type", "SH"),
                put_call=gc("putcall"),
                investment_discretion=gc("discretion"),
                other_manager=gc("other"),
                voting_sole=_int(gc("sole").replace(",", "")),
                voting_shared=_int(gc("shared").replace(",", "")),
                voting_none=_int(gc("none").replace(",", "")),
            ))
        except Exception:
            continue

    data = FilingData(holdings=holdings)
    data.compute_totals()
    return data


def _map_html_columns(headers: list[str]) -> dict[str, int]:
    """Map logical field names to column indices based on header text."""
    mapping: dict[str, int] = {}
    for i, h in enumerate(headers):
        h_lower = h.lower()
        if "issuer" in h_lower or ("name" in h_lower and "other" not in h_lower):
            mapping.setdefault("name", i)
        elif "title" in h_lower or "class" in h_lower:
            mapping.setdefault("class", i)
        elif "cusip" in h_lower:
            mapping["cusip"] = i
        elif "value" in h_lower:
            mapping.setdefault("value", i)
        elif "share" in h_lower or "principal" in h_lower or "amount" in h_lower:
            mapping.setdefault("shares", i)
        elif "type" in h_lower or "prn" in h_lower:
            mapping.setdefault("type", i)
        elif "put" in h_lower or "call" in h_lower:
            mapping["putcall"] = i
        elif "discretion" in h_lower:
            mapping["discretion"] = i
        elif "other manager" in h_lower:
            mapping["other"] = i
        elif "sole" in h_lower:
            mapping["sole"] = i
        elif "shared" in h_lower:
            mapping["shared"] = i
        elif "none" in h_lower:
            mapping["none"] = i
    return mapping


def _int(val: str) -> int:
    if not val:
        return 0
    try:
        return int(re.sub(r"[^\d]", "", val))
    except ValueError:
        return 0


# ── QoQ Comparison ────────────────────────────────────────────────────────────

@dataclass
class HoldingDelta:
    cusip: str
    issuer_name: str
    ticker: str
    change_type: str          # "new", "exit", "add", "trim", "unchanged", "changed_instrument"
    current: Optional[Holding]
    prior: Optional[Holding]

    @property
    def value_change_usd_thousands(self) -> int:
        cv = self.current.value_usd_thousands if self.current else 0
        pv = self.prior.value_usd_thousands if self.prior else 0
        return cv - pv

    @property
    def shares_change(self) -> int:
        cs = self.current.shares_or_principal if self.current else 0
        ps = self.prior.shares_or_principal if self.prior else 0
        return cs - ps

    @property
    def label(self) -> str:
        if self.ticker:
            return f"{self.issuer_name} ({self.ticker})"
        return self.issuer_name


def compare_filings(current: FilingData, prior: FilingData) -> list[HoldingDelta]:
    """
    CUSIP-first comparison of two FilingData objects.
    Returns a list of HoldingDelta entries categorized as:
    new, exit, add, trim, unchanged, or changed_instrument.
    """
    current_map: dict[str, Holding] = {}
    for h in current.holdings:
        key = h.cusip.upper().strip()
        if key:
            current_map[key] = h

    prior_map: dict[str, Holding] = {}
    for h in prior.holdings:
        key = h.cusip.upper().strip()
        if key:
            prior_map[key] = h

    deltas: list[HoldingDelta] = []
    all_cusips = set(current_map) | set(prior_map)

    for cusip in all_cusips:
        cur = current_map.get(cusip)
        prr = prior_map.get(cusip)
        issuer = (cur or prr).issuer_name
        ticker = (cur or prr).ticker

        if cur and not prr:
            change_type = "new"
        elif prr and not cur:
            change_type = "exit"
        else:
            assert cur is not None and prr is not None
            # Both present — compare share/principal amount
            if cur.shares_or_principal > prr.shares_or_principal:
                change_type = "add"
            elif cur.shares_or_principal < prr.shares_or_principal:
                change_type = "trim"
            elif cur.put_call != prr.put_call or cur.title_of_class != prr.title_of_class:
                change_type = "changed_instrument"
            else:
                change_type = "unchanged"

        deltas.append(HoldingDelta(
            cusip=cusip,
            issuer_name=issuer,
            ticker=ticker,
            change_type=change_type,
            current=cur,
            prior=prr,
        ))

    return deltas
