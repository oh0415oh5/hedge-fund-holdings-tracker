"""Unit tests for the EDGAR utilities."""

import pytest
from src.edgar import _pad_cik, FilingRecord


class TestPadCik:
    def test_short_cik(self):
        assert _pad_cik("1067983") == "0001067983"

    def test_already_padded(self):
        assert _pad_cik("0001067983") == "0001067983"

    def test_with_dashes(self):
        assert _pad_cik("CIK0001067983") == "0001067983"

    def test_numeric_string(self):
        assert _pad_cik("12345") == "0000012345"

    def test_ten_digits(self):
        assert _pad_cik("1234567890") == "1234567890"


class TestFilingRecord:
    def _make(self, accession: str = "0001193125-26-226661") -> FilingRecord:
        return FilingRecord(
            filer_name="TEST CORP",
            cik="0001067983",
            form_type="13F-HR",
            period_of_report="2026-03-31",
            filed_date="2026-05-15",
            accession_number=accession,
            edgar_url="https://www.sec.gov/",
        )

    def test_accession_nodash(self):
        rec = self._make("0001193125-26-226661")
        assert rec.accession_nodash == "000119312526226661"

    def test_is_amendment_false(self):
        rec = self._make()
        assert rec.is_amendment is False

    def test_full_submission_url_format(self):
        rec = self._make()
        url = rec.full_submission_url
        assert "edgar/data" in url
        assert "1067983" in url
        assert "index.htm" in url
