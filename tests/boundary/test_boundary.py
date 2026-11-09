"""Information boundary (SPEC 18.4)."""

import ast
import dataclasses
import gc
from pathlib import Path

import numpy as np

from marginbench.config import public_config
from marginbench.environment.actions import legal_actions
from marginbench.environment.engine import Engine
from marginbench.environment.observations import (
    OBSERVABLE_EVENT_KEYS,
    ObservationLeakError,
    observation_record,
    request_view,
    validate_allowlist,
    validate_observation_record,
)
from marginbench.environment.state import RequestState, check_visibility_registry, vf
from marginbench.hashing import canonical_json
from marginbench.schemas import Visibility
from helpers import run_p0, small_cfg

SRC = Path(__file__).resolve().parents[2] / "src" / "marginbench"


class Recorder:
    name = "REC"

    def __init__(self):
        from marginbench.policies.baseline import P0Baseline

        self.inner = P0Baseline(use_prior=True)
        self.obs, self.legal, self.feedback, self.reset_args = [], [], [], None

    def reset(self, pub, est, obs):
        self.reset_args = (pub, est, obs)
        self.inner.reset(pub, est, obs)

    def act(self, observation, legal):
        self.obs.append(observation)
        self.legal.append(legal)
        return self.inner.act(observation, legal)

    def observe_feedback(self, events):
        self.feedback.extend(events)

    def diagnostics(self):
        return {}


def test_registry_and_allowlist_valid():
    check_visibility_registry()
    validate_allowlist()


def test_new_latent_field_leaves_observation_unchanged():
    Extended = dataclasses.make_dataclass(
        "Extended", [("secret_risk", float, vf(Visibility.LATENT, 0.123))], bases=(RequestState,))
    base = RequestState(request_id="R1", property_id="P00", tenant_id="T", category="hvac")
    ext = Extended(request_id="R1", property_id="P00", tenant_id="T", category="hvac", secret_risk=9.9)
    assert canonical_json(request_view(base)) == canonical_json(request_view(ext))


def test_unknown_observation_fields_rejected():
    rec = Recorder()
    run_p0(small_cfg(), policy=rec)
    r = observation_record(rec.obs[0])
    r["request"]["true_severity"] = "urgent"
    try:
        validate_observation_record(r)
    except ObservationLeakError:
        pass
    else:
        raise AssertionError("unknown field accepted")


def test_evaluator_only_never_in_feedback():
    rec = Recorder()
    run_p0(small_cfg(), policy=rec)
    assert rec.feedback
    banned = {"success", "p_success", "true_severity", "physically_resolved", "negligent", "operator_cents",
              "owner_cents", "hazard", "kind", "cohort"}
    for e in rec.feedback:
        keys = {k for k, _ in e.data}
        assert keys <= set(OBSERVABLE_EVENT_KEYS[e.type])
        assert not keys & banned


def test_mutating_observation_does_not_change_engine():
    rec = Recorder()
    eng, out, _ = run_p0(small_cfg(), policy=rec)
    o = rec.obs[-1]
    before = out.requests[o.request.request_id].stage
    try:
        o.request.stage = "CLOSED"  # frozen
    except dataclasses.FrozenInstanceError:
        pass
    object.__setattr__(o.request, "stage", "HACKED")
    assert out.requests[o.request.request_id].stage == before


def test_policies_do_not_import_environment():
    for py in (SRC / "policies").rglob("*.py"):
        tree = ast.parse(py.read_text())
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [n.name for n in node.names]
            elif isinstance(node, ast.ImportFrom):
                mods = [node.module or ""]
            for m in mods:
                assert "environment" not in m and "economics" not in m and "evaluation" not in m, (py, m)


def _reachable(roots, limit=200_000):
    import inspect

    seen, stack, out = set(), list(roots), []
    while stack and len(seen) < limit:
        x = stack.pop()
        if id(x) in seen or isinstance(x, (type, type(gc))) or inspect.isroutine(x):
            continue
        seen.add(id(x))
        out.append(x)
        stack.extend(gc.get_referents(x))
    assert len(seen) < limit
    return out


def test_no_reference_path_to_engine():
    from marginbench.economics.ledger import Ledger
    from marginbench.environment.arrivals import World
    from marginbench.environment.randomness import StreamFactory
    from marginbench.environment.state import ContractorState, ContractState, PropertyState, TenantState

    rec = Recorder()
    run_p0(small_cfg(), policy=rec)
    roots = [rec.reset_args, rec.obs[:20], rec.legal[:20], rec.feedback[:50]]
    forbidden = (Engine, RequestState, ContractorState, PropertyState, TenantState, ContractState, World,
                 StreamFactory, Ledger, np.random.Generator)
    for x in _reachable(roots):
        assert not isinstance(x, forbidden), type(x)


def test_seeds_not_recoverable_from_policy_inputs():
    cfg = small_cfg()
    master, rep = 987_654_321, 4242
    rec = Recorder()
    run_p0(cfg, partition="dev", rep=rep, policy=rec, master_seed=master)
    blob = canonical_json(rec.reset_args[0]) + "".join(canonical_json(o) for o in rec.obs) + \
        "".join(canonical_json(e) for e in rec.feedback)
    for s in (str(master), str(rep), '"dev"', "sim-1.0|"):
        assert s not in blob
    # MC seeds do not depend on the master seed: same request ids and decision indices give the same seed
    rec2 = Recorder()
    run_p0(cfg, partition="dev", rep=rep, policy=rec2, master_seed=master + 1)
    first1, first2 = {}, {}
    for o in rec.obs:
        first1.setdefault(o.request.request_id, o.mc_seed)  # decision index 0
    for o in rec2.obs:
        first2.setdefault(o.request.request_id, o.mc_seed)
    common = set(first1) & set(first2)
    for rid in common:
        assert first1[rid] == first2[rid]
    env_seeds = set()
    from marginbench.environment.randomness import StreamFactory

    sf = StreamFactory(cfg.versions.sim_version, "dev", master, rep)
    for rid in first1:
        for mech in ("repair", "report", "callback", "request_latent", "info", "duration", "verify"):
            env_seeds.add(sf.seed(mech, rid, 0))
    assert not env_seeds & set(first1.values())


def test_legal_actions_independent_of_latent_state():
    cfg = small_cfg()
    eng, out, _ = run_p0(cfg)
    pub = public_config(cfg)
    tick = eng.end_tick - 1
    checked = 0
    for rid, req in sorted(out.requests.items()):
        if req.handed_over or req.stage.value not in ("NEW", "DISPATCH_READY", "WORK_REPORTED", "VERIFIED_OK", "VERIFIED_FAIL"):
            continue
        o1 = eng.observation(req, tick)
        l1 = legal_actions(o1, pub)
        req.true_severity = "urgent" if req.true_severity != "urgent" else "minor"
        req.physical_resolved = not req.physical_resolved
        req.unreported_failure = True
        for c in eng.contractors.values():
            c.logit_success += 3.0
        eng.properties[req.property_id].condition = 0.01
        eng.tenants[req.tenant_id].report_propensity = 0.0
        o2 = eng.observation(req, tick)
        assert canonical_json(o1) == canonical_json(o2)
        assert legal_actions(o2, pub) == l1
        checked += 1
    # also check a synthetic decision-stage request
    from marginbench.schemas import Stage

    req = RequestState(request_id="ZZ", property_id="P00", tenant_id="P00T0", category="hvac",
                       stage=Stage.DISPATCH_READY, sla_tier="minor", sla_deadline_tick=tick + 5 * 1440)
    l1 = legal_actions(eng.observation(req, tick), pub)
    req.true_severity = "urgent"
    req.physical_resolved = True
    assert legal_actions(eng.observation(req, tick), pub) == l1
