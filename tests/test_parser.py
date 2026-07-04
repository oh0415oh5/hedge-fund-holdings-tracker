"""Unit tests for the 13F information-table parser and QoQ comparison."""

import pytest
from src.parser import (
    Holding,
    FilingData,
    HoldingDelta,
    parse_info_table,
    compare_filings,
    _int,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

MINIMAL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<informationTable xmlns="https://www.sec.gov/13F">
  <infoTable>
    <nameOfIssuer>APPLE INC</nameOfIssuer>
    <titleOfClass>COM</titleOfClass>
    <cusip>037833100</cusip>
    <value>100000</value>
    <shrsOrPrnAmt>
      <sshPrnamt>5000000</sshPrnamt>
      <sshPrnamtType>SH</sshPrnamtType>
    </shrsOrPrnAmt>
    <putCall></putCall>
    <investmentDiscretion>SOLE</investmentDiscretion>
    <votingAuthority>
      <Sole>5000000</Sole>
      <Shared>0</Shared>
      <None>0</None>
    </votingAuthority>
  </infoTable>
  <infoTable>
    <nameOfIssuer>MICROSOFT CORP</nameOfIssuer>
    <titleOfClass>COM</titleOfClass>
    <cusip>594918104</cusip>
    <value>50000</value>
    <shrsOrPrnAmt>
      <sshPrnamt>1000000</sshPrnamt>
      <sshPrnamtType>SH</sshPrnamtType>
    </shrsOrPrnAmt>
    <putCall>Put</putCall>
    <investmentDiscretion>SOLE</investmentDiscretion>
    <votingAuthority>
      <Sole>0</Sole>
      <Shared>0</Shared>
      <None>1000000</None>
    </votingAuthority>
  </infoTable>
</informationTable>
"""

NAMESPACED_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ns1:informationTable xmlns:ns1="http://www.sec.gov/cgi-bin/viewer?action=view">
  <ns1:infoTable>
    <ns1:nameOfIssuer>GOOGLE LLC</ns1:nameOfIssuer>
    <ns1:titleOfClass>CL A</ns1:titleOfClass>
    <ns1:cusip>02079K305</ns1:cusip>
    <ns1:value>200000</ns1:value>
    <ns1:shrsOrPrnAmt>
      <ns1:sshPrnamt>750000</ns1:sshPrnamt>
      <ns1:sshPrnamtType>SH</ns1:sshPrnamtType>
    </ns1:shrsOrPrnAmt>
    <ns1:putCall></ns1:putCall>
    <ns1:investmentDiscretion>SOLE</ns1:investmentDiscretion>
    <ns1:votingAuthority>
      <ns1:Sole>750000</ns1:Sole>
      <ns1:Shared>0</ns1:Shared>
      <ns1:None>0</ns1:None>
    </ns1:votingAuthority>
  </ns1:infoTable>
</ns1:informationTable>
"""


# ── Parser tests ──────────────────────────────────────────────────────────────

class TestParseInfoTable:
    def test_parses_basic_xml(self):
        data = parse_info_table(MINIMAL_XML)
        assert data.holding_count == 2
        assert data.holdings[0].issuer_name == "APPLE INC"
        assert data.holdings[0].cusip == "037833100"
        assert data.holdings[0].value_usd_thousands == 100_000
        assert data.holdings[0].shares_or_principal == 5_000_000

    def test_detects_put_call(self):
        data = parse_info_table(MINIMAL_XML)
        assert data.has_put_call is True
        put_holding = next(h for h in data.holdings if h.put_call == "Put")
        assert put_holding.issuer_name == "MICROSOFT CORP"

    def test_no_put_call_when_absent(self):
        data = parse_info_table(NAMESPACED_XML)
        assert data.has_put_call is False

    def test_parses_namespaced_xml(self):
        data = parse_info_table(NAMESPACED_XML)
        assert data.holding_count == 1
        assert data.holdings[0].cusip == "02079K305"
        assert data.holdings[0].shares_or_principal == 750_000

    def test_total_value(self):
        data = parse_info_table(MINIMAL_XML)
        assert data.total_value_usd_thousands == 150_000
        assert data.total_value_usd_millions == pytest.approx(150.0)

    def test_empty_xml(self):
        data = parse_info_table("<informationTable></informationTable>")
        assert data.holding_count == 0
        assert data.total_value_usd_thousands == 0

    def test_value_usd_properties(self):
        data = parse_info_table(MINIMAL_XML)
        h = data.holdings[0]
        assert h.value_usd == 100_000 * 1000
        assert h.value_usd_millions == pytest.approx(100.0)


# ── _int helper ───────────────────────────────────────────────────────────────

class TestIntHelper:
    def test_plain_integer(self):
        assert _int("12345") == 12_345

    def test_comma_separated(self):
        assert _int("1,234,567") == 1_234_567

    def test_empty_string(self):
        assert _int("") == 0

    def test_non_numeric(self):
        assert _int("N/A") == 0

    def test_with_dollar_sign(self):
        assert _int("$5,000") == 5_000


# ── QoQ comparison ────────────────────────────────────────────────────────────

def _make_holding(cusip: str, shares: int, value: int, put_call: str = "") -> Holding:
    return Holding(
        issuer_name=f"ISSUER_{cusip}",
        title_of_class="COM",
        cusip=cusip,
        value_usd_thousands=value,
        shares_or_principal=shares,
        share_type="SH",
        put_call=put_call,
        investment_discretion="SOLE",
        other_manager="",
        voting_sole=shares,
        voting_shared=0,
        voting_none=0,
    )


def _make_filing(*holdings: Holding) -> FilingData:
    fd = FilingData(holdings=list(holdings))
    fd.compute_totals()
    return fd


class TestCompareFilings:
    def test_new_position(self):
        current = _make_filing(_make_holding("AAA111", 100, 1000))
        prior = _make_filing()
        deltas = compare_filings(current, prior)
        assert len(deltas) == 1
        assert deltas[0].change_type == "new"
        assert deltas[0].cusip == "AAA111"

    def test_exit(self):
        current = _make_filing()
        prior = _make_filing(_make_holding("BBB222", 200, 2000))
        deltas = compare_filings(current, prior)
        assert len(deltas) == 1
        assert deltas[0].change_type == "exit"

    def test_add(self):
        current = _make_filing(_make_holding("CCC333", 300, 3000))
        prior = _make_filing(_make_holding("CCC333", 100, 1000))
        deltas = compare_filings(current, prior)
        assert len(deltas) == 1
        assert deltas[0].change_type == "add"
        assert deltas[0].shares_change == 200

    def test_trim(self):
        current = _make_filing(_make_holding("DDD444", 50, 500))
        prior = _make_filing(_make_holding("DDD444", 200, 2000))
        deltas = compare_filings(current, prior)
        assert len(deltas) == 1
        assert deltas[0].change_type == "trim"
        assert deltas[0].shares_change == -150

    def test_unchanged(self):
        h = _make_holding("EEE555", 100, 1000)
        current = _make_filing(h)
        prior = _make_filing(_make_holding("EEE555", 100, 1000))
        deltas = compare_filings(current, prior)
        assert len(deltas) == 1
        assert deltas[0].change_type == "unchanged"

    def test_mixed(self):
        current = _make_filing(
            _make_holding("NEW111", 100, 1000),
            _make_holding("ADD222", 200, 2000),
        )
        prior = _make_filing(
            _make_holding("ADD222", 100, 1000),
            _make_holding("EXIT333", 50, 500),
        )
        deltas = compare_filings(current, prior)
        by_type = {d.cusip: d.change_type for d in deltas}
        assert by_type["NEW111"] == "new"
        assert by_type["ADD222"] == "add"
        assert by_type["EXIT333"] == "exit"

    def test_cusip_case_insensitive(self):
        current = _make_filing(_make_holding("abc123", 100, 1000))
        prior = _make_filing(_make_holding("ABC123", 200, 2000))
        deltas = compare_filings(current, prior)
        assert len(deltas) == 1
        assert deltas[0].change_type == "trim"

    def test_value_change_calculation(self):
        current = _make_filing(_make_holding("FFF666", 500, 5000))
        prior = _make_filing(_make_holding("FFF666", 200, 2000))
        deltas = compare_filings(current, prior)
        assert deltas[0].value_change_usd_thousands == 3000

    def test_changed_instrument(self):
        current = _make_filing(_make_holding("GGG777", 100, 1000, put_call="Put"))
        prior = _make_filing(_make_holding("GGG777", 100, 1000, put_call="Call"))
        deltas = compare_filings(current, prior)
        assert deltas[0].change_type == "changed_instrument"


# ── Holding label ─────────────────────────────────────────────────────────────

class TestHoldingLabel:
    def test_label_without_ticker(self):
        h = _make_holding("AAA111", 100, 1000)
        assert h.label == "ISSUER_AAA111"

    def test_label_with_high_confidence_ticker(self):
        h = _make_holding("AAA111", 100, 1000)
        h.ticker = "AAPL"
        h.ticker_confidence = "high"
        assert "AAPL" in h.label

    def test_label_with_low_confidence_ticker(self):
        h = _make_holding("AAA111", 100, 1000)
        h.ticker = "AAPL"
        h.ticker_confidence = "low"
        assert h.label == "ISSUER_AAA111"
