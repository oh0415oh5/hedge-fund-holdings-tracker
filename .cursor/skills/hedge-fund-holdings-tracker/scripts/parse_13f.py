"""Parse 13F information table XML into structured holdings."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class Holding:
    issuer_name: str
    title_of_class: str
    cusip: str
    value_usd: int
    shares_or_principal: float
    share_or_principal_type: str
    put_call: str
    investment_discretion: str
    other_manager: str
    voting_sole: int
    voting_shared: int
    voting_none: int
    ticker: str | None = None
    mapping_confidence: str = "unresolved"

    @property
    def is_put_call(self) -> bool:
        return self.put_call.upper() in {"PUT", "CALL"}


@dataclass
class HoldingsSnapshot:
    holdings: list[Holding] = field(default_factory=list)

    @property
    def total_reported_value(self) -> int:
        return sum(h.value_usd for h in self.holdings)

    def top_by_value(self, n: int = 10) -> list[Holding]:
        return sorted(self.holdings, key=lambda h: h.value_usd, reverse=True)[:n]


def _local(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _find(row: ET.Element, *names: str) -> ET.Element | None:
    for name in names:
        found = row.find(f".//{{*}}{name}")
        if found is not None:
            return found
        found = row.find(name)
        if found is not None:
            return found
    return None


def _text(node: ET.Element | None, default: str = "") -> str:
    if node is None or node.text is None:
        return default
    return node.text.strip()


def _int_text(node: ET.Element | None, default: int = 0) -> int:
    text = _text(node)
    if not text:
        return default
    return int(float(text.replace(",", "")))


def _float_text(node: ET.Element | None, default: float = 0.0) -> float:
    text = _text(node)
    if not text:
        return default
    return float(text.replace(",", ""))


def parse_information_table(xml_bytes: bytes) -> HoldingsSnapshot:
    root = ET.fromstring(xml_bytes)
    holdings: list[Holding] = []

    info_rows: Iterable[ET.Element]
    if _local(root.tag).lower() == "informationtable":
        info_rows = root.findall(".//{*}infoTable")
        if not info_rows:
            info_rows = root.findall(".//infoTable")
    else:
        info_rows = root.findall(".//{*}infoTable")
        if not info_rows:
            info_rows = root.findall(".//infoTable")

    for row in info_rows:
        shares_parent = _find(row, "shrsOrPrnAmt")
        voting_parent = _find(row, "votingAuthority")
        holdings.append(
            Holding(
                issuer_name=_text(_find(row, "nameOfIssuer")),
                title_of_class=_text(_find(row, "titleOfClass")),
                cusip=_text(_find(row, "cusip")),
                value_usd=_int_text(_find(row, "value")),
                shares_or_principal=_float_text(
                    _find(shares_parent, "sshPrnamt") if shares_parent is not None else _find(row, "sshPrnamt")
                ),
                share_or_principal_type=_text(
                    _find(shares_parent, "sshPrnamtType")
                    if shares_parent is not None
                    else _find(row, "sshPrnamtType")
                ),
                put_call=_text(_find(row, "putCall")),
                investment_discretion=_text(_find(row, "investmentDiscretion")),
                other_manager=_text(_find(row, "otherManager")),
                voting_sole=_int_text(
                    _find(voting_parent, "Sole") if voting_parent is not None else _find(row, "Sole")
                ),
                voting_shared=_int_text(
                    _find(voting_parent, "Shared")
                    if voting_parent is not None
                    else _find(row, "Shared")
                ),
                voting_none=_int_text(
                    _find(voting_parent, "None") if voting_parent is not None else _find(row, "None")
                ),
            )
        )

    return HoldingsSnapshot(holdings=holdings)
