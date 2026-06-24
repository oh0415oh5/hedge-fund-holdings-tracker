"""SEC EDGAR client for 13F filing discovery and retrieval."""

from __future__ import annotations

import json
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import requests

SEC_BASE = "https://www.sec.gov"
DATA_BASE = "https://data.sec.gov"
DEFAULT_USER_AGENT = "hedge-fund-holdings-tracker research@wallstreetprompt.com"


@dataclass(frozen=True)
class FilingRef:
    cik: str
    accession_number: str
    filing_type: str
    filing_date: str
    report_date: str
    primary_document: str
    company_name: str
    is_amendment: bool

    @property
    def accession_no_dashes(self) -> str:
        return self.accession_number.replace("-", "")

    @property
    def edgar_filing_url(self) -> str:
        cik_int = str(int(self.cik))
        return (
            f"{SEC_BASE}/cgi-bin/viewer"
            f"?action=view&cik={cik_int}&accession_number={self.accession_number}"
            f"&xbrl_type=v"
        )

    @property
    def edgar_index_url(self) -> str:
        cik_int = str(int(self.cik))
        return (
            f"{SEC_BASE}/Archives/edgar/data/{cik_int}/"
            f"{self.accession_no_dashes}/{self.accession_number}-index.htm"
        )


class EdgarClient:
    def __init__(self, user_agent: str = DEFAULT_USER_AGENT) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept-Encoding": "gzip, deflate",
            }
        )

    def _get(self, url: str) -> requests.Response:
        time.sleep(0.12)
        response = self.session.get(url, timeout=60)
        response.raise_for_status()
        return response

    def normalize_cik(self, cik: str) -> str:
        digits = re.sub(r"\D", "", cik)
        if not digits:
            raise ValueError(f"Invalid CIK: {cik}")
        return digits.zfill(10)

    def get_company_submissions(self, cik: str) -> dict[str, Any]:
        normalized = self.normalize_cik(cik)
        url = f"{DATA_BASE}/submissions/CIK{normalized}.json"
        return self._get(url).json()

    def list_13f_filings(self, cik: str, limit: int = 8) -> list[FilingRef]:
        payload = self.get_company_submissions(cik)
        company_name = payload.get("name", "Unknown filer")
        normalized = self.normalize_cik(cik)
        filings: list[FilingRef] = []

        recent = payload.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accessions = recent.get("accessionNumber", [])
        filing_dates = recent.get("filingDate", [])
        report_dates = recent.get("reportDate", [])
        primary_docs = recent.get("primaryDocument", [])

        for idx, form in enumerate(forms):
            if not form.startswith("13F"):
                continue
            filings.append(
                FilingRef(
                    cik=normalized,
                    accession_number=accessions[idx],
                    filing_type=form,
                    filing_date=filing_dates[idx],
                    report_date=report_dates[idx],
                    primary_document=primary_docs[idx],
                    company_name=company_name,
                    is_amendment=form.endswith("/A"),
                )
            )
            if len(filings) >= limit:
                break

        return filings

    def _filing_folder_url(self, filing: FilingRef) -> str:
        cik_int = str(int(filing.cik))
        return (
            f"{SEC_BASE}/Archives/edgar/data/{cik_int}/"
            f"{filing.accession_no_dashes}/"
        )

    def _find_information_table_url(self, filing: FilingRef) -> str:
        index_url = self._filing_folder_url(filing)
        index_payload = self._get(f"{index_url}index.json").json()
        items = index_payload.get("directory", {}).get("item", [])

        for item in items:
            name = item.get("name", "")
            lowered = name.lower()
            if name.endswith(".xml") and "infotable" in lowered:
                return urljoin(index_url, name)

        xml_candidates = [
            item
            for item in items
            if item.get("name", "").endswith(".xml")
            and item.get("name") != "primary_doc.xml"
        ]
        xml_candidates.sort(key=lambda item: int(item.get("size", 0)), reverse=True)

        for item in xml_candidates:
            name = item.get("name", "")
            probe_url = urljoin(index_url, name)
            snippet = self._get(probe_url).content[:4000].decode("utf-8", errors="ignore")
            if "informationTable" in snippet or "infoTable" in snippet:
                return probe_url

        if xml_candidates:
            return urljoin(index_url, xml_candidates[0]["name"])

        raise FileNotFoundError(
            f"No information table XML found for accession {filing.accession_number}"
        )

    def fetch_information_table_xml(self, filing: FilingRef) -> bytes:
        url = self._find_information_table_url(filing)
        return self._get(url).content

    def resolve_cik_by_name(self, name: str) -> list[dict[str, str]]:
        url = f"{SEC_BASE}/cgi-bin/browse-edgar"
        params = {
            "company": name,
            "owner": "include",
            "action": "getcompany",
            "output": "json",
        }
        try:
            payload = self._get(f"{url}?company={requests.utils.quote(name)}&owner=include&action=getcompany&output=json")
            data = payload.json()
        except (requests.HTTPError, json.JSONDecodeError):
            return []

        hits: list[dict[str, str]] = []
        for entry in data if isinstance(data, list) else data.get("hits", {}).get("hits", []):
            source = entry.get("_source", entry)
            hits.append(
                {
                    "name": source.get("entity", source.get("name", "")),
                    "cik": str(source.get("ciks", [source.get("cik", "")])[0]).zfill(10),
                }
            )
        return hits
