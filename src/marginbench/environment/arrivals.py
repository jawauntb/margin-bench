"""Policy-independent world generation: entities and the exogenous arrival list (SPEC 5.1-5.3).

Everything here is generated before a run starts from keyed streams, so every policy arm
in a replication sees the identical opportunity list and latent attributes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from marginbench.config import CATEGORIES, SEVERITIES, Config
from marginbench.environment.contractors import ContractorDraw, draw_contractors
from marginbench.environment.randomness import StreamFactory

DAY = 1440


@dataclass(frozen=True)
class PropertyDraw:
    property_id: str
    owner_id: str
    contract_id: str
    unit_count: int
    risk: float
    condition: float
    condition_obs: float


@dataclass(frozen=True)
class TenantDraw:
    tenant_id: str
    unit_id: str
    property_id: str
    report_propensity: float


@dataclass(frozen=True)
class Opportunity:
    opportunity_id: str
    property_id: str
    unit_id: str
    tenant_id: str
    category: str
    tick: int
    true_severity: str
    reported_severity: str
    info_severity: str  # reported severity after a request_info resample


@dataclass(frozen=True)
class World:
    streams: StreamFactory
    properties: tuple[PropertyDraw, ...]
    tenants: tuple[TenantDraw, ...]
    contractors: tuple[ContractorDraw, ...]
    opportunities: tuple[Opportunity, ...]  # sorted by (tick, opportunity_id)


def seasonal_factor(cfg: Config, category: str, day: np.ndarray) -> np.ndarray:
    if category != "hvac" or not cfg.arrivals.seasonal:
        return np.ones_like(day, dtype=float)
    a = cfg.arrivals.hvac_season_amplitude
    return 1.0 + a * np.cos(2.0 * np.pi * (day - cfg.arrivals.hvac_season_peak_day) / 365.0)


def _report(true_idx: int, accuracy: float, u1: float, u2: float) -> str:
    if u1 < accuracy:
        return SEVERITIES[true_idx]
    adj = [i for i in (true_idx - 1, true_idx + 1) if 0 <= i < len(SEVERITIES)]
    pick = adj[0] if len(adj) == 1 else adj[int(u2 < 0.5)]
    return SEVERITIES[pick]


def build_world(cfg: Config, streams: StreamFactory, horizon_days: int) -> World:
    pc = cfg.portfolio
    props: list[PropertyDraw] = []
    tenants: list[TenantDraw] = []
    sigma = pc.property_risk_log_sd
    for p in range(pc.n_properties):
        pid = f"P{p:02d}"
        g = streams.gen("property", pid, 0)
        z = float(g.standard_normal())
        q = float(g.beta(pc.condition_beta_a, pc.condition_beta_b))
        noise = float(g.standard_normal())
        risk = math.exp(-0.5 * sigma * sigma + sigma * z) if cfg.arrivals.heterogeneous else 1.0
        q_obs = q if cfg.obs.perfect else min(1.0, max(0.0, q + pc.condition_obs_noise_sd * noise))
        props.append(PropertyDraw(pid, f"W{p:02d}", f"K{p:02d}", pc.units_per_property, risk, q, q_obs))
        for u in range(pc.units_per_property):
            uid = f"{pid}U{u}"
            tid = f"{pid}T{u}"
            tg = streams.gen("tenant", tid, 0)
            rho = float(tg.beta(pc.tenant_report_beta_a, pc.tenant_report_beta_b))
            tenants.append(TenantDraw(tid, uid, pid, rho))

    contractors = draw_contractors(cfg, streams)

    gen_days = cfg.time.generation_days
    days = np.arange(gen_days, dtype=float)
    acc = cfg.sev_accuracy()
    opps: list[Opportunity] = []
    for prop in props:
        for u in range(prop.unit_count):
            uid = f"{prop.property_id}U{u}"
            tid = f"{prop.property_id}T{u}"
            for cat in CATEGORIES:
                lam = (
                    cfg.arrivals.base_rate_per_unit_day
                    * cfg.arrivals.rate_multiplier
                    * cfg.arrivals.shares[cat]
                    * prop.risk
                    * seasonal_factor(cfg, cat, days)
                )
                g = streams.gen("arrivals", f"{uid}|{cat}", 0)
                counts = g.poisson(lam)
                n_total = int(counts.sum())
                minutes = g.integers(0, DAY, size=n_total) if n_total else np.zeros(0, dtype=int)
                pos = 0
                n = 0
                for d in range(gen_days):
                    c = int(counts[d])
                    if c == 0:
                        continue
                    for m in sorted(int(x) for x in minutes[pos : pos + c]):
                        if d < horizon_days:
                            oid = f"{uid}-{cat[:2]}-{n:04d}"
                            opps.append(_make_opportunity(cfg, streams, oid, prop.property_id, uid, tid, cat, d * DAY + m, acc))
                        n += 1
                    pos += c
    opps.sort(key=lambda o: (o.tick, o.opportunity_id))
    return World(streams, tuple(props), tuple(tenants), contractors, tuple(opps))


def _make_opportunity(
    cfg: Config, streams: StreamFactory, oid: str, pid: str, uid: str, tid: str, cat: str, tick: int, acc: float
) -> Opportunity:
    g = streams.gen("request_latent", oid, 0)
    u_sev, u1, u2 = (float(x) for x in g.random(3))
    probs = cfg.severity.probs[cat]
    cum = np.cumsum(probs)
    true_idx = int(min(int(np.searchsorted(cum, u_sev, side="right")), len(SEVERITIES) - 1))
    reported = _report(true_idx, acc, u1, u2)
    gi = streams.gen("info", oid, 0)
    v1, v2 = (float(x) for x in gi.random(2))
    info_acc = 1.0 if cfg.obs.perfect else cfg.obs.info_accuracy
    info_sev = _report(true_idx, info_acc, v1, v2)
    return Opportunity(oid, pid, uid, tid, cat, tick, SEVERITIES[true_idx], reported, info_sev)
