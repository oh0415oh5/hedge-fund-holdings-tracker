"""Unit tests for chart generation — verifies each chart returns a valid PNG data URI."""

import pytest
from src.parser import FilingData, Holding, HoldingDelta
from src.charts import (
    chart_top10_holdings,
    chart_concentration,
    chart_qoq_attribution,
    chart_put_call_exposure,
    build_all_charts,
)


def _make_holding(name: str, cusip: str, value_k: int, shares: int, put_call: str = "") -> Holding:
    return Holding(
        issuer_name=name,
        title_of_class="COM",
        cusip=cusip,
        value_usd_thousands=value_k,
        shares_or_principal=shares,
        share_type="SH",
        put_call=put_call,
        investment_discretion="SOLE",
        other_manager="",
        voting_sole=shares,
        voting_shared=0,
        voting_none=0,
    )


def _sample_filing(n: int = 15) -> FilingData:
    holdings = [
        _make_holding(f"COMPANY {i}", f"CUSIP{i:06d}", (15 - i) * 10_000, (15 - i) * 100_000)
        for i in range(n)
    ]
    fd = FilingData(holdings=holdings)
    fd.compute_totals()
    return fd


def _is_png_data_uri(s: str) -> bool:
    return isinstance(s, str) and s.startswith("data:image/png;base64,") and len(s) > 100


class TestChartTop10:
    def test_returns_data_uri(self):
        data = _sample_filing()
        result = chart_top10_holdings(data)
        assert _is_png_data_uri(result)

    def test_empty_filing_returns_empty_string(self):
        empty = FilingData()
        empty.compute_totals()
        assert chart_top10_holdings(empty) == ""


class TestChartConcentration:
    def test_returns_data_uri(self):
        data = _sample_filing()
        result = chart_concentration(data)
        assert _is_png_data_uri(result)

    def test_zero_total_returns_empty_string(self):
        empty = FilingData()
        empty.compute_totals()
        assert chart_concentration(empty) == ""


class TestChartQoQ:
    def _make_delta(self, cusip: str, change_type: str, cur_val: int = 1000, pri_val: int = 0) -> HoldingDelta:
        cur = _make_holding("A", cusip, cur_val, 100) if cur_val else None
        pri = _make_holding("A", cusip, pri_val, 50) if pri_val else None
        return HoldingDelta(
            cusip=cusip,
            issuer_name="A",
            ticker="",
            change_type=change_type,
            current=cur,
            prior=pri,
        )

    def test_returns_data_uri_with_changes(self):
        deltas = [
            self._make_delta("N1", "new", cur_val=1000),
            self._make_delta("E1", "exit", cur_val=0, pri_val=500),
            self._make_delta("A1", "add", cur_val=2000, pri_val=1000),
            self._make_delta("T1", "trim", cur_val=300, pri_val=1000),
        ]
        result = chart_qoq_attribution(deltas)
        assert _is_png_data_uri(result)

    def test_returns_data_uri_with_no_changes(self):
        result = chart_qoq_attribution([])
        assert _is_png_data_uri(result)


class TestChartPutCall:
    def test_returns_none_when_no_put_call(self):
        data = _sample_filing()
        assert chart_put_call_exposure(data) is None

    def test_returns_data_uri_with_put_call(self):
        holdings = [
            _make_holding("COMPANY A", "AAA111", 50_000, 100_000, put_call="Put"),
            _make_holding("COMPANY B", "BBB222", 30_000, 80_000, put_call="Call"),
            _make_holding("COMPANY A", "AAA111", 20_000, 40_000, put_call="Call"),
        ]
        fd = FilingData(holdings=holdings)
        fd.compute_totals()
        result = chart_put_call_exposure(fd)
        assert result is not None
        assert _is_png_data_uri(result)


class TestBuildAllCharts:
    def test_all_keys_present(self):
        data = _sample_filing()
        charts = build_all_charts(data, deltas=None)
        assert set(charts.keys()) == {"top10", "concentration", "qoq", "put_call"}

    def test_qoq_none_when_no_deltas(self):
        data = _sample_filing()
        charts = build_all_charts(data, deltas=None)
        assert charts["qoq"] is None

    def test_put_call_none_when_no_put_call_rows(self):
        data = _sample_filing()
        charts = build_all_charts(data, deltas=None)
        assert charts["put_call"] is None

    def test_top10_and_concentration_always_present(self):
        data = _sample_filing()
        charts = build_all_charts(data, deltas=None)
        assert _is_png_data_uri(charts["top10"])
        assert _is_png_data_uri(charts["concentration"])
