"""SEC EDGAR API client for 13F filing discovery and retrieval."""

from __future__ import annotations

import re
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Optional

import requests

BASE = "https://data.sec.gov"
EFTS = "https://efts.sec.gov/LATEST/search-index"
SUBMISSIONS = f"{BASE}/submissions"
FILING_DATA = "https://www.sec.gov/Archives/edgar/data"

HEADERS = {
    "User-Agent": "WallStreetPrompt research@wallstreetprompt.com",
    "Accept-Encoding": "gzip, deflate",
    "Accept": "application/json, text/html, application/xml",
}

# Throttle: SEC allows ~10 req/s; stay under 8
_LAST_REQUEST: float = 0.0
_RATE_LIMIT_DELAY = 0.125  # seconds between requests


def _get(url: str, **kwargs) -> requests.Response:
    global _LAST_REQUEST
    elapsed = time.time() - _LAST_REQUEST
    if elapsed < _RATE_LIMIT_DELAY:
        time.sleep(_RATE_LIMIT_DELAY - elapsed)
    resp = requests.get(url, headers=HEADERS, timeout=30, **kwargs)
    _LAST_REQUEST = time.time()
    resp.raise_for_status()
    return resp


@dataclass
class FilerInfo:
    name: str
    cik: str  # zero-padded 10-digit string
    sic: str = ""
    state: str = ""


@dataclass
class FilingRecord:
    filer_name: str
    cik: str
    form_type: str
    period_of_report: str
    filed_date: str
    accession_number: str  # formatted: XXXXXXXXXX-XX-XXXXXX
    is_amendment: bool = False
    amendment_info: str = ""
    edgar_url: str = ""
    info_table_url: str = ""

    @property
    def accession_nodash(self) -> str:
        return self.accession_number.replace("-", "")

    @property
    def filing_index_url(self) -> str:
        return (
            f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
            f"&CIK={self.cik}&type=13F-HR&dateb=&owner=include&count=40"
        )

    @property
    def full_submission_url(self) -> str:
        return (
            f"https://www.sec.gov/Archives/edgar/data/"
            f"{int(self.cik)}/{self.accession_nodash}/{self.accession_number}-index.htm"
        )


def search_filer(query: str) -> list[FilerInfo]:
    """Search EDGAR for filers matching a name query. Returns top candidates."""
    url = f"https://efts.sec.gov/LATEST/search-index?q=%22{urllib.parse.quote(query)}%22&dateRange=custom&startdt=2000-01-01&forms=13F-HR&hits.hits._source=period_of_report,file_date,entity_name,file_num,period_of_report"
    # Fall back to company search API
    company_url = f"https://www.sec.gov/cgi-bin/browse-edgar?company={urllib.parse.quote(query)}&CIK=&type=13F-HR&dateb=&owner=include&count=20&search_text=&action=getcompany&output=atom"
    
    results: list[FilerInfo] = []
    try:
        resp = _get(f"{BASE}/submissions/CIK{_pad_cik(query)}.json")
        data = resp.json()
        results.append(FilerInfo(
            name=data.get("name", query),
            cik=_pad_cik(str(data.get("cik", query))),
            sic=str(data.get("sic", "")),
            state=data.get("stateOfIncorporation", ""),
        ))
        return results
    except Exception:
        pass

    # Full-text search fallback
    try:
        search_url = (
            f"https://efts.sec.gov/LATEST/search-index"
            f"?q=%22{urllib.parse.quote(query)}%22&forms=13F-HR&hits.hits.total.value=true"
        )
        data = _get(search_url).json()
        for hit in data.get("hits", {}).get("hits", [])[:5]:
            src = hit.get("_source", {})
            entity = src.get("entity_name") or src.get("display_names", [None])[0]
            cik_val = src.get("file_num", "") or hit.get("_id", "")
            if entity:
                results.append(FilerInfo(name=entity, cik=cik_val))
    except Exception:
        pass

    return results


def _pad_cik(cik: str) -> str:
    """Return a 10-digit zero-padded CIK string."""
    digits = re.sub(r"[^0-9]", "", cik)
    return digits.zfill(10)


def get_filer_by_cik(cik: str) -> FilerInfo:
    """Fetch filer metadata for a given CIK."""
    padded = _pad_cik(cik)
    url = f"{SUBMISSIONS}/CIK{padded}.json"
    data = _get(url).json()
    return FilerInfo(
        name=data.get("name", ""),
        cik=padded,
        sic=str(data.get("sic", "")),
        state=data.get("stateOfIncorporation", ""),
    )


def get_13f_filings(cik: str, max_filings: int = 10) -> list[FilingRecord]:
    """Return a list of 13F-HR (and 13F-HR/A) filings for the given CIK, newest first."""
    padded = _pad_cik(cik)
    url = f"{SUBMISSIONS}/CIK{padded}.json"
    data = _get(url).json()
    filer_name = data.get("name", "")

    filings: list[FilingRecord] = []
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    periods = recent.get("reportDate", [])

    for form, date, acc, period in zip(forms, dates, accessions, periods):
        if form in ("13F-HR", "13F-HR/A"):
            is_amend = form.endswith("/A")
            filings.append(FilingRecord(
                filer_name=filer_name,
                cik=padded,
                form_type=form,
                period_of_report=period,
                filed_date=date,
                accession_number=acc,
                is_amendment=is_amend,
                amendment_info="Amendment" if is_amend else "",
                edgar_url=(
                    f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
                    f"&CIK={padded}&type=13F-HR&dateb=&owner=include&count=40"
                ),
            ))
        if len(filings) >= max_filings:
            break

    # Also page through older filings if needed
    if len(filings) < 2:
        for page_key in ("files",):
            for file_entry in data.get("filings", {}).get(page_key, []):
                additional_url = f"{SUBMISSIONS}/CIK{padded}/{file_entry.get('name', '')}"
                try:
                    more = _get(additional_url).json()
                    af, ad, aa, ap = (
                        more.get("form", []),
                        more.get("filingDate", []),
                        more.get("accessionNumber", []),
                        more.get("reportDate", []),
                    )
                    for form, date, acc, period in zip(af, ad, aa, ap):
                        if form in ("13F-HR", "13F-HR/A"):
                            is_amend = form.endswith("/A")
                            filings.append(FilingRecord(
                                filer_name=filer_name,
                                cik=padded,
                                form_type=form,
                                period_of_report=period,
                                filed_date=date,
                                accession_number=acc,
                                is_amendment=is_amend,
                                amendment_info="Amendment" if is_amend else "",
                                edgar_url=(
                                    f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
                                    f"&CIK={padded}&type=13F-HR&dateb=&owner=include&count=40"
                                ),
                            ))
                except Exception:
                    continue

    return filings


def get_filing_documents(filing: FilingRecord) -> dict[str, str]:
    """
    Retrieve the filing index and return a mapping of document type → URL.
    Looks for the 13F information table document (XML or HTML).
    """
    padded = _pad_cik(filing.cik)
    acc_nodash = filing.accession_nodash
    index_url = (
        f"https://www.sec.gov/Archives/edgar/data/{int(padded)}/{acc_nodash}/{filing.accession_number}-index.htm"
    )
    docs: dict[str, str] = {"index": index_url}

    try:
        from bs4 import BeautifulSoup
        resp = _get(index_url)
        soup = BeautifulSoup(resp.text, "lxml")
        table = soup.find("table", {"class": "tableFile"})
        if not table:
            table = soup.find("table")
        if table:
            for row in table.find_all("tr")[1:]:
                cells = row.find_all("td")
                if len(cells) >= 3:
                    desc = cells[1].get_text(strip=True).lower() if len(cells) > 1 else ""
                    href = cells[2].find("a", href=True)
                    if href:
                        doc_url = f"https://www.sec.gov{href['href']}"
                        if "information table" in desc or "infotable" in desc:
                            docs["info_table"] = doc_url
                        elif "13f" in desc or "primary" in desc:
                            docs["primary"] = doc_url
                        elif href["href"].endswith(".xml") and "info" in desc:
                            docs["info_table_xml"] = doc_url
        
        # Fallback: scan all links for the info table XML
        if "info_table" not in docs and "info_table_xml" not in docs:
            for a in soup.find_all("a", href=True):
                href_val = a["href"]
                if "infotable" in href_val.lower() or ("information" in a.get_text(strip=True).lower() and href_val.endswith(".xml")):
                    docs["info_table"] = f"https://www.sec.gov{href_val}"
                    break
    except Exception as exc:
        docs["_error"] = str(exc)

    return docs


def download_info_table(filing: FilingRecord) -> str:
    """
    Download and return the raw text of the 13F information table
    (XML preferred, HTML fallback).
    """
    docs = get_filing_documents(filing)
    url = docs.get("info_table") or docs.get("info_table_xml")

    if not url:
        # Try constructing common filenames
        padded = _pad_cik(filing.cik)
        acc_nodash = filing.accession_nodash
        base = f"https://www.sec.gov/Archives/edgar/data/{int(padded)}/{acc_nodash}"
        for candidate in ("infotable.xml", "form13fInfoTable.xml", "13F_INFO.xml", "information_table.xml"):
            try:
                resp = _get(f"{base}/{candidate}")
                if resp.status_code == 200:
                    return resp.text
            except Exception:
                continue

        # Last resort: grab full-text filing index JSON
        try:
            json_url = f"https://data.sec.gov/submissions/CIK{padded}.json"
            idx_url = f"https://www.sec.gov/Archives/edgar/data/{int(padded)}/{acc_nodash}/{filing.accession_number}-index.json"
            resp = _get(idx_url)
            index_data = resp.json()
            for item in index_data.get("items", []):
                if "infotable" in item.get("name", "").lower() or "information" in item.get("description", "").lower():
                    file_url = f"{base}/{item['name']}"
                    return _get(file_url).text
        except Exception:
            pass

        raise ValueError(
            f"Cannot locate information table document for filing {filing.accession_number}. "
            f"Available docs: {docs}"
        )

    return _get(url).text
