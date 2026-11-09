"""Verification inspection (SPEC 5.7)."""

from __future__ import annotations

from marginbench.config import Config


def verification_result(cfg: Config, physically_resolved: bool, u: float) -> str:
    sens, spec = cfg.verify_rates()
    if physically_resolved:
        return "ok" if u < spec else "fail"
    return "fail" if u < sens else "ok"
