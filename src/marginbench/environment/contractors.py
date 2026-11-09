"""Contractor fixtures, per-replication perturbation, and capacity scheduling (SPEC 5.4)."""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass

import numpy as np
from scipy.stats import spearmanr

from marginbench.config import CATEGORIES, Config
from marginbench.environment.randomness import StreamFactory

DAY = 1440
WORK_DAY_START = 480  # 08:00
SLOT_MINUTES = 120
SLOTS_PER_DAY = 8


def logit(p: float) -> float:
    return math.log(p / (1.0 - p))


def expit(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)


@dataclass(frozen=True)
class ContractorDraw:
    contractor_id: str
    price_multiplier: float
    eligible: tuple[str, ...]
    speed: float
    capacity: int  # effective; 0 = unlimited
    logit_success: float
    category_offsets: tuple[tuple[str, float], ...]


def _rank_corr_assignment(values: list[float], quality: list[float], target: float) -> list[float]:
    """Permutation of ``values`` whose Spearman correlation with ``quality`` is closest to
    ``target``; ties broken by the lexicographically smallest permutation index tuple."""
    n = len(values)
    best: tuple[float, tuple[int, ...]] | None = None
    for perm in itertools.permutations(range(n)):
        assigned = [values[i] for i in perm]
        if len(set(assigned)) == 1 or len(set(quality)) == 1:
            rho = 0.0
        else:
            rho = float(spearmanr(assigned, quality).statistic)
        cand = (abs(rho - target), perm)
        if best is None or cand < best:
            best = cand
    assert best is not None
    return [values[i] for i in best[1]]


def fixture_speeds_prices(cfg: Config) -> tuple[list[float], list[float]]:
    fx = cfg.contractors.fixtures
    quality = [f.success for f in fx]
    speeds = [f.speed for f in fx]
    prices = [f.price for f in fx]
    if cfg.contractors.speed_quality_corr is not None:
        speeds = _rank_corr_assignment(speeds, quality, cfg.contractors.speed_quality_corr)
    if cfg.contractors.price_quality_corr is not None:
        prices = _rank_corr_assignment(prices, quality, cfg.contractors.price_quality_corr)
    return speeds, prices


def draw_contractors(cfg: Config, streams: StreamFactory) -> tuple[ContractorDraw, ...]:
    cc = cfg.contractors
    fx = cc.fixtures
    speeds, prices = fixture_speeds_prices(cfg)
    base_logits = [logit(f.success) for f in fx]
    mean_logit = float(np.mean(base_logits))
    out = []
    for i, f in enumerate(fx):
        g = streams.gen("contractor", f.id, 0)
        z_logit, z_price = g.standard_normal(2)
        z_off = g.standard_normal(len(CATEGORIES))
        if cc.identical_quality:
            lg = logit(cc.identical_quality_value)
            offs = {k: 0.0 for k in CATEGORIES}
        else:
            lg = mean_logit + cc.success_dispersion * (base_logits[i] - mean_logit) + cc.logit_success_sd * float(z_logit)
            offs = {k: cc.category_offset_sd * float(z_off[j]) for j, k in enumerate(CATEGORIES)}
        if cc.identical_price:
            price = 1.0
        else:
            price = prices[i] * (1.0 + cc.price_sd * float(z_price))
            price = max(price, 0.05)
        if cc.unlimited_capacity:
            cap = 0
        else:
            cap = max(1, int(math.floor(cc.capacity_multiplier * f.capacity)))
        out.append(
            ContractorDraw(
                contractor_id=f.id,
                price_multiplier=float(price),
                eligible=tuple(f.eligible),
                speed=float(speeds[i]),
                capacity=cap,
                logit_success=float(lg),
                category_offsets=tuple((k, offs[k]) for k in CATEGORIES),
            )
        )
    return tuple(out)


def earliest_start_day(dispatch_tick: int, base_lead_days: float, speed: float) -> int:
    return dispatch_tick // DAY + int(math.ceil(base_lead_days / speed - 1e-12))


def find_slot(schedule: dict[int, int], capacity: int, first_day: int) -> tuple[int, int]:
    """Earliest day >= first_day with free capacity, and the slot index on that day.
    capacity 0 means unlimited."""
    day = first_day
    if capacity <= 0:
        return day, schedule.get(day, 0)
    while schedule.get(day, 0) >= capacity:
        day += 1
    return day, schedule.get(day, 0)


def slot_start_tick(day: int, slot: int) -> int:
    return (day + slot // SLOTS_PER_DAY) * DAY + WORK_DAY_START + SLOT_MINUTES * (slot % SLOTS_PER_DAY)


def preview_start_tick(schedule: dict[int, int], capacity: int, dispatch_tick: int, base_lead_days: float, speed: float) -> int:
    day, slot = find_slot(schedule, capacity, earliest_start_day(dispatch_tick, base_lead_days, speed))
    return slot_start_tick(day, slot)


def book_slot(schedule: dict[int, int], capacity: int, dispatch_tick: int, base_lead_days: float, speed: float) -> int:
    day, slot = find_slot(schedule, capacity, earliest_start_day(dispatch_tick, base_lead_days, speed))
    schedule[day] = slot + 1
    return slot_start_tick(day, slot)


def overtime_start_tick(dispatch_tick: int, delay_minutes: int, speed: float) -> int:
    return dispatch_tick + int(math.ceil(delay_minutes / speed - 1e-12))
