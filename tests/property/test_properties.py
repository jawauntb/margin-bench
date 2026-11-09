"""Property tests (SPEC 18.3) over random small worlds and seeds."""

import math

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from marginbench.config import load_config
from marginbench.environment.callbacks import callback_probability
from marginbench.environment.repairs import success_probability
from marginbench.evaluation.validation import validate_transitions
from marginbench.schemas import Stage
from helpers import SMALL, run_p0

SETTINGS = settings(max_examples=12, deadline=None, suppress_health_check=[HealthCheck.too_slow])

overlays = st.fixed_dictionaries({
    "arrivals": st.fixed_dictionaries({"rate_multiplier": st.sampled_from([0.0, 0.5, 1.0, 3.0])}),
    "contractors": st.fixed_dictionaries({
        "capacity_multiplier": st.sampled_from([0.5, 1.0, 2.0]),
        "unlimited_capacity": st.booleans(),
    }),
    "callbacks": st.fixed_dictionaries({"off": st.booleans(), "consume_capacity": st.booleans()}),
    "verify": st.fixed_dictionaries({"perfect": st.booleans()}),
    "loss": st.fixed_dictionaries({"hazard_multiplier": st.sampled_from([0.0, 1.0, 50.0])}),
})


def cfg_from(ov):
    return load_config(overlays=[SMALL, ov])


@SETTINGS
@given(ov=overlays, rep=st.integers(0, 10_000))
def test_run_invariants(ov, rep):
    cfg = cfg_from(ov)
    eng, out, world = run_p0(cfg, rep=rep)
    assert out.status == "VALID"
    # no impossible transitions
    assert validate_transitions(out.events) == []
    # monotone ticks
    ticks = [e.tick for e in out.events]
    assert ticks == sorted(ticks)
    # no negative capacity, no over-booking
    for c in out.contractors.values():
        for day, used in c.schedule.items():
            assert used >= 0
            if c.capacity > 0:
                assert used <= c.capacity
    # ledger entries reference existing events and requests; no duplicate fee/expense entries
    ev_ids = {e.event_id for e in out.events}
    keys = set()
    for e in out.ledger.entries:
        assert e.event_id in ev_ids
        if e.request_id is not None:
            assert e.request_id in out.requests
        k = (e.event_id, e.principal, e.category, e.contract_id)
        assert k not in keys
        keys.add(k)
    # physical_resolved never reverts and closure never implies repair
    for r in out.requests.values():
        if r.resolved_tick is not None:
            assert r.physical_resolved
    if ov["arrivals"]["rate_multiplier"] == 0.0:
        assert len(out.requests) == 0
        assert all(e.category == "fee_revenue" for e in out.ledger.entries)


class RecordingPolicy:
    name = "REC"

    def __init__(self):
        from marginbench.policies.baseline import P0Baseline

        self.inner = P0Baseline(use_prior=True)
        self.seen = []

    def reset(self, pub, est, obs):
        self.inner.reset(pub, est, obs)

    def act(self, observation, legal):
        self.seen.append(observation)
        return self.inner.act(observation, legal)

    def observe_feedback(self, events):
        self.seen_feedback = getattr(self, "seen_feedback", []) + list(events)

    def diagnostics(self):
        return {}


@SETTINGS
@given(rep=st.integers(0, 10_000))
def test_no_future_events_in_observations(rep):
    cfg = cfg_from({})
    pol = RecordingPolicy()
    _, out, _ = run_p0(cfg, rep=rep, policy=pol)
    for o in pol.seen:
        assert o.day == o.tick // 1440
        assert o.request.arrival_tick <= o.tick
        for a in o.request.attempts:
            assert a.dispatch_tick <= o.tick
            if a.start_tick is not None:
                assert a.start_tick <= o.tick
        if o.request.first_closure_tick is not None:
            assert o.request.first_closure_tick <= o.tick
    for e in getattr(pol, "seen_feedback", []):
        assert e.tick <= max(o.tick for o in pol.seen)


@given(lg=st.floats(-8, 8), off=st.floats(-2, 2), q=st.floats(0, 1), j=st.integers(0, 20),
       sev=st.sampled_from(["minor", "moderate", "urgent"]), rho=st.floats(0, 1), cu=st.booleans())
def test_probabilities_in_unit_interval(lg, off, q, j, sev, rho, cu):
    cfg = load_config()
    p = success_probability(cfg, lg, off, sev, q, j)
    assert 0.0 <= p <= 1.0
    c = callback_probability(cfg, rho, sev, cu)
    assert 0.0 <= c <= 1.0


def _fixture_run(success_value):
    ov = {"contractors": {"identical_quality": True, "identical_quality_value": success_value,
                          "category_offset_sd": 0.0},
          "repair": {"b_sev": {"minor": 0.0, "moderate": 0.0, "urgent": 0.0}, "condition_coef": 0.0,
                     "attempt_coef": 0.0}}
    return run_p0(cfg_from(ov))


def test_all_success_fixture():
    _, out, _ = _fixture_run(0.999999999)
    assert out.status == "VALID"
    for r in out.requests.values():
        if r.attempts and r.attempts[0].success is not None:
            assert r.attempts[0].success is True
    assert validate_transitions(out.events) == []


def test_all_failure_fixture():
    _, out, _ = _fixture_run(1e-9)
    assert out.status == "VALID"
    for r in out.requests.values():
        for a in r.attempts:
            if a.success is not None:
                assert a.success is False
        assert not r.physical_resolved
    assert validate_transitions(out.events) == []


def test_zero_arrivals_fixture():
    _, out, _ = run_p0(cfg_from({"arrivals": {"rate_multiplier": 0.0}}))
    assert out.status == "VALID" and out.requests == {}
    days = cfg_from({}).time.horizon_days
    assert sum(1 for e in out.ledger.entries if e.category == "fee_revenue") == 5 * days
