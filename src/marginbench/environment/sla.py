"""Service levels and credits (SPEC 5.9)."""

from __future__ import annotations

from marginbench.config import Config


def sla_deadline(cfg: Config, arrival_tick: int, tier: str) -> int:
    return arrival_tick + 60 * cfg.sla.target_hours[tier]


def sla_credit_cents(cfg: Config, tier: str) -> int:
    return int(round(cfg.sla.credit[tier] * 100))
