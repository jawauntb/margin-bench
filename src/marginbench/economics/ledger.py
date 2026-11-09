"""Append-only ledger in integer cents (SPEC 6)."""

from __future__ import annotations

from collections import defaultdict
from typing import Optional

from marginbench.schemas import EntryStatus, LedgerEntry, Principal

CATEGORIES = (
    "fee_revenue",
    "dispatch_expense",
    "verification_expense",
    "callback_expense",
    "escalation_expense",
    "info_expense",
    "sla_credit_paid",
    "sla_credit_received",
    "repair_invoice",
    "severe_loss",
)

# Allowed payer/receiver and sign for each category (payer-misattribution check).
CATEGORY_RULES: dict[str, tuple[frozenset[Principal], int]] = {
    "fee_revenue": (frozenset({Principal.OPERATOR}), +1),
    "dispatch_expense": (frozenset({Principal.OPERATOR}), -1),
    "verification_expense": (frozenset({Principal.OPERATOR}), -1),
    "callback_expense": (frozenset({Principal.OPERATOR}), -1),
    "escalation_expense": (frozenset({Principal.OPERATOR}), -1),
    "info_expense": (frozenset({Principal.OPERATOR}), -1),
    "sla_credit_paid": (frozenset({Principal.OPERATOR}), -1),
    "sla_credit_received": (frozenset({Principal.OWNER}), +1),
    "repair_invoice": (frozenset({Principal.OWNER}), -1),
    "severe_loss": (frozenset({Principal.OWNER, Principal.OPERATOR}), -1),
}

# Operator expense categories that make up proxy OPEX (SPEC 8): excludes severe-loss shares.
PROXY_OPEX_CATEGORIES = frozenset(
    {"dispatch_expense", "verification_expense", "callback_expense", "escalation_expense", "info_expense", "sla_credit_paid"}
)


class Ledger:
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.entries: list[LedgerEntry] = []

    def post(
        self,
        *,
        event_id: int,
        tick: int,
        principal: Principal,
        category: str,
        amount_cents: int,
        contract_id: str,
        request_id: Optional[str] = None,
        action_id: Optional[str] = None,
        status: EntryStatus = EntryStatus.REALIZED,
    ) -> LedgerEntry:
        if category not in CATEGORY_RULES:
            raise ValueError(f"unknown ledger category {category}")
        if not isinstance(amount_cents, int):
            raise TypeError("ledger amounts must be integer cents")
        e = LedgerEntry(
            entry_id=len(self.entries),
            run_id=self.run_id,
            event_id=event_id,
            tick=tick,
            principal=principal,
            category=category,
            amount_cents=amount_cents,
            contract_id=contract_id,
            request_id=request_id,
            action_id=action_id,
            status=status,
        )
        self.entries.append(e)
        return e

    def totals_by_principal(self) -> dict[str, int]:
        out: dict[str, int] = defaultdict(int)
        for e in self.entries:
            out[e.principal.value] += e.amount_cents
        return dict(out)

    def totals_by_principal_category(self) -> dict[tuple[str, str], int]:
        out: dict[tuple[str, str], int] = defaultdict(int)
        for e in self.entries:
            out[(e.principal.value, e.category)] += e.amount_cents
        return dict(out)

    def operator_daily(self, n_days: int) -> list[int]:
        out = [0] * n_days
        for e in self.entries:
            if e.principal == Principal.OPERATOR:
                d = e.tick // 1440
                if 0 <= d < n_days:
                    out[d] += e.amount_cents
        return out
