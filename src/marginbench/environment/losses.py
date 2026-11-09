"""Severe loss (SPEC 5.10)."""

from __future__ import annotations

import math

from marginbench.config import Config


def loss_amount_cents(cfg: Config, true_severity: str, z: float) -> int:
    med = cfg.loss.median_amount[true_severity]
    return int(round(med * math.exp(cfg.loss.log_sd * z) * 100))


def split_loss(cfg: Config, amount_cents: int, negligent: bool) -> tuple[int, int]:
    """Returns (operator_cents, owner_cents); both non-negative and summing to amount."""
    op = int(round(amount_cents * cfg.loss.operator_negligence_share)) if negligent else 0
    return op, amount_cents - op
