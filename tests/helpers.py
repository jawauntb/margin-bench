"""Shared test helpers (not a test module)."""

from __future__ import annotations

from typing import Any, Optional

from marginbench.config import load_config, public_config
from marginbench.environment.arrivals import build_world
from marginbench.environment.engine import Engine, RunSpec
from marginbench.environment.randomness import StreamFactory, run_nonce
from marginbench.policies.baseline import P0Baseline

SMALL = {
    "time": {"warmup_days": 3, "decision_days": 10, "maturation_days": 10, "proxy_cutoff_offset_days": 3,
             "history_days": 30, "generation_days": 40},
    "portfolio": {"n_properties": 5},
}


def small_cfg(extra: Optional[list[dict[str, Any]]] = None):
    return load_config(overlays=[SMALL] + (extra or []))


def run_p0(cfg, partition: str = "dev", rep: int = 0, policy: Any = None, master_seed: Optional[int] = None,
           nonce_key: Optional[int] = None):
    pub = public_config(cfg)
    ms = cfg.seeds.master(partition) if master_seed is None else master_seed
    sf = StreamFactory(cfg.versions.sim_version, partition, ms, rep)
    world = build_world(cfg, sf, cfg.time.horizon_days)
    p0 = P0Baseline(use_prior=True)
    p0.reset(pub, None, None)
    arm = p0
    if policy is not None:
        policy.reset(pub, None, None)
        arm = policy
    nk = cfg.seeds.nonce_key if nonce_key is None else nonce_key
    eng = Engine(cfg, world, RunSpec(f"t-{partition}-{rep}", cfg.time.horizon_days, run_nonce(nk, partition, rep)), arm, p0)
    out = eng.run()
    return eng, out, world
