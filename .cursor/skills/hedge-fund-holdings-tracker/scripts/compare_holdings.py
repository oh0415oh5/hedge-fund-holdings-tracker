"""Quarter-over-quarter holdings comparison."""

from __future__ import annotations

from dataclasses import dataclass

from parse_13f import Holding, HoldingsSnapshot


@dataclass
class PositionChange:
    cusip: str
    issuer_name: str
    put_call: str
    change_type: str
    prior_value: int
    current_value: int
    prior_shares: float
    current_shares: float
    value_delta: int
    share_delta: float


@dataclass
class ComparisonSummary:
    new_positions: list[PositionChange]
    exits: list[PositionChange]
    adds: list[PositionChange]
    trims: list[PositionChange]
    unchanged_count: int


def _key(holding: Holding) -> tuple[str, str]:
    return (holding.cusip, holding.put_call.upper())


def compare_snapshots(
    current: HoldingsSnapshot, prior: HoldingsSnapshot
) -> ComparisonSummary:
    current_map = {_key(h): h for h in current.holdings}
    prior_map = {_key(h): h for h in prior.holdings}

    new_positions: list[PositionChange] = []
    exits: list[PositionChange] = []
    adds: list[PositionChange] = []
    trims: list[PositionChange] = []
    unchanged_count = 0

    for key, current_h in current_map.items():
        prior_h = prior_map.get(key)
        if prior_h is None:
            new_positions.append(
                PositionChange(
                    cusip=current_h.cusip,
                    issuer_name=current_h.issuer_name,
                    put_call=current_h.put_call,
                    change_type="new",
                    prior_value=0,
                    current_value=current_h.value_usd,
                    prior_shares=0.0,
                    current_shares=current_h.shares_or_principal,
                    value_delta=current_h.value_usd,
                    share_delta=current_h.shares_or_principal,
                )
            )
            continue

        share_delta = current_h.shares_or_principal - prior_h.shares_or_principal
        value_delta = current_h.value_usd - prior_h.value_usd
        if share_delta > 0:
            adds.append(
                PositionChange(
                    cusip=current_h.cusip,
                    issuer_name=current_h.issuer_name,
                    put_call=current_h.put_call,
                    change_type="add",
                    prior_value=prior_h.value_usd,
                    current_value=current_h.value_usd,
                    prior_shares=prior_h.shares_or_principal,
                    current_shares=current_h.shares_or_principal,
                    value_delta=value_delta,
                    share_delta=share_delta,
                )
            )
        elif share_delta < 0:
            trims.append(
                PositionChange(
                    cusip=current_h.cusip,
                    issuer_name=current_h.issuer_name,
                    put_call=current_h.put_call,
                    change_type="trim",
                    prior_value=prior_h.value_usd,
                    current_value=current_h.value_usd,
                    prior_shares=prior_h.shares_or_principal,
                    current_shares=current_h.shares_or_principal,
                    value_delta=value_delta,
                    share_delta=share_delta,
                )
            )
        else:
            unchanged_count += 1

    for key, prior_h in prior_map.items():
        if key not in current_map:
            exits.append(
                PositionChange(
                    cusip=prior_h.cusip,
                    issuer_name=prior_h.issuer_name,
                    put_call=prior_h.put_call,
                    change_type="exit",
                    prior_value=prior_h.value_usd,
                    current_value=0,
                    prior_shares=prior_h.shares_or_principal,
                    current_shares=0.0,
                    value_delta=-prior_h.value_usd,
                    share_delta=-prior_h.shares_or_principal,
                )
            )

    adds.sort(key=lambda c: c.value_delta, reverse=True)
    trims.sort(key=lambda c: c.value_delta)
    new_positions.sort(key=lambda c: c.current_value, reverse=True)
    exits.sort(key=lambda c: c.prior_value, reverse=True)

    return ComparisonSummary(
        new_positions=new_positions,
        exits=exits,
        adds=adds,
        trims=trims,
        unchanged_count=unchanged_count,
    )


def concentration_buckets(snapshot: HoldingsSnapshot) -> dict[str, float]:
    total = snapshot.total_reported_value or 1
    ranked = sorted(snapshot.holdings, key=lambda h: h.value_usd, reverse=True)

    def bucket_sum(n: int) -> int:
        return sum(h.value_usd for h in ranked[:n])

    top5 = bucket_sum(5)
    top10 = bucket_sum(10)
    top25 = bucket_sum(25)
    return {
        "top5_pct": 100 * top5 / total,
        "top10_pct": 100 * (top10 - top5) / total,
        "top25_pct": 100 * (top25 - top10) / total,
        "remainder_pct": 100 * (total - top25) / total,
        "top5_value": top5,
        "top10_value": top10,
        "top25_value": top25,
        "total_value": total,
    }
