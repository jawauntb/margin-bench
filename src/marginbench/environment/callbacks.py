"""Tenant callbacks and benign repeats (SPEC 5.8)."""

from __future__ import annotations

from typing import Optional

from marginbench.config import Config

DAY = 1440


def callback_probability(cfg: Config, rho: float, true_severity: str, closed_unverified: bool) -> float:
    if cfg.callbacks.off:
        return 0.0
    m_close = cfg.m_close_unverified() if closed_unverified else 1.0
    return min(1.0, max(0.0, rho * cfg.m_sev(true_severity) * m_close))


def callback_delay_minutes(cfg: Config, gamma_draw_days: float) -> int:
    """gamma_draw_days ~ Gamma(shape, 1); scaled by the configured scale (days)."""
    return max(1, int(round(gamma_draw_days * cfg.callbacks.delay_gamma_scale_days * DAY)))


def benign_repeat_delay(cfg: Config, u_occ: float, u_time: float) -> Optional[int]:
    if cfg.callbacks.off or u_occ >= cfg.callbacks.benign_prob:
        return None
    return max(1, int(u_time * cfg.callbacks.benign_window_days * DAY))
