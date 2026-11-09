"""Management-contract fee accrual in exact integer cents (SPEC 5.12)."""

from __future__ import annotations


def annual_fee_cents(per_unit_month_dollars: float, units: int) -> int:
    per_unit_month_cents = int(round(per_unit_month_dollars * 100))
    return per_unit_month_cents * 12 * units


def cumulative_fee_cents(annual_cents: int, n_days: int) -> int:
    """Fees booked through the first ``n_days`` days of the contract.

    floor(n * annual / 365): the remainder is carried forward, so any 365 consecutive
    days starting at day 0 book exactly ``annual_cents``."""
    return (n_days * annual_cents) // 365


def daily_fee_cents(annual_cents: int, day_index: int) -> int:
    """Fee booked on contract day ``day_index`` (0-based)."""
    return cumulative_fee_cents(annual_cents, day_index + 1) - cumulative_fee_cents(annual_cents, day_index)
