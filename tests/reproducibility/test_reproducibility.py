"""Reproducibility (SPEC 18.5)."""

import numpy as np

from marginbench.config import public_config
from marginbench.economics.reconciliation import replay_entries
from marginbench.environment.arrivals import build_world
from marginbench.environment.randomness import StreamFactory
from marginbench.policies.baseline import BehaviorPolicy
from helpers import run_p0, small_cfg

CFG = small_cfg()


def test_identical_runs_identical_hashes():
    _, a, _ = run_p0(CFG, rep=3)
    _, b, _ = run_p0(CFG, rep=3)
    assert a.event_hash == b.event_hash
    assert a.ledger_hash == b.ledger_hash


def test_changing_only_policy_leaves_arrivals_identical():
    _, a, wa = run_p0(CFG, rep=1)
    _, b, wb = run_p0(CFG, rep=1, policy=BehaviorPolicy(0.7))
    assert wa.opportunities == wb.opportunities
    arr_a = [(e.request_id, e.tick) for e in a.events if e.type in ("ARRIVAL", "OPPORTUNITY_UNSERVED")]
    arr_b = [(e.request_id, e.tick) for e in b.events if e.type in ("ARRIVAL", "OPPORTUNITY_UNSERVED")]
    assert arr_a == arr_b
    assert a.event_hash != b.event_hash  # the policies did act differently


def test_keyed_draws_independent_of_processing_order():
    sf = StreamFactory("sim-1.0", "dev", 7, 0)
    x1 = sf.uniforms("repair", "R1", 0, 3)
    _ = sf.uniforms("repair", "R2", 0, 50)
    x2 = sf.uniforms("repair", "R1", 0, 3)
    assert np.array_equal(x1, x2)
    w1 = build_world(CFG, sf, CFG.time.horizon_days)
    _ = build_world(CFG, StreamFactory("sim-1.0", "dev", 8, 0), CFG.time.horizon_days)
    w2 = build_world(CFG, sf, CFG.time.horizon_days)
    assert w1 == w2


def test_arrival_prefix_stable_across_horizons():
    long = small_cfg([{"time": {"maturation_days": 20}}])
    sf = StreamFactory("sim-1.0", "dev", 7, 0)
    a = build_world(CFG, sf, CFG.time.horizon_days).opportunities
    b = [o for o in build_world(long, sf, long.time.horizon_days).opportunities if o.tick < CFG.time.horizon_days * 1440]
    assert list(a) == b


def test_different_master_seeds_diverge():
    _, a, _ = run_p0(CFG, master_seed=1)
    _, b, _ = run_p0(CFG, master_seed=2)
    assert a.event_hash != b.event_hash


def test_replay_reconstructs_ledger():
    _, out, _ = run_p0(CFG, rep=2)
    cids = sorted(out.contracts)
    cp = {k: v.property_id for k, v in out.contracts.items()}
    rep = replay_entries(out.events, CFG, out.run_id, cids, cp)
    assert [e.to_record() for e in rep] == [e.to_record() for e in out.ledger.entries]
