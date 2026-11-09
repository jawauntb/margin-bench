"""Legal and illegal transitions (SPEC 7)."""

import dataclasses

import pytest

from marginbench.config import public_config
from marginbench.environment.actions import legal_actions
from marginbench.schemas import Action, ActionType, AttemptView, ContractorView, Observation, PropertyView, RequestView, Stage
from helpers import run_p0, small_cfg

CFG = small_cfg()
PUB = public_config(CFG)


def contractors():
    out = []
    for cid, elig in (("A", ("plumbing", "hvac", "general")), ("B", ("plumbing", "electrical", "hvac", "general")),
                      ("C", ("plumbing", "electrical", "hvac", "general")), ("D", ("plumbing", "electrical", "hvac", "general"))):
        out.append(ContractorView(cid, 1.0, elig, 1.0, 3, 0, 2000, 400, 0, 0, 0))
    return tuple(out)


def obs(stage, **kw):
    base = dict(request_id="R", property_id="P00", tenant_id="T", category="electrical", arrival_tick=0,
                reported_severity="moderate", stage=stage, attempt_index=0, observed_failure_count=0, defer_count=0,
                info_requested=False, sla_tier="moderate", sla_deadline_tick=72 * 60, sla_breached=False,
                first_start_tick=None, first_closure_tick=None, last_close_unverified=False, callback_count=0,
                reopened_by_callback=False, had_severe_loss=False, attempts=())
    base.update(kw)
    prop = PropertyView("P00", "W00", "K00", 10, 0.7, "ACTIVE", 39.45, 0, 0, 0, 0)
    return Observation(0, 0, RequestView(**base), prop, contractors(), 1, 0)


def labels(acts):
    return [a.label() for a in acts]


def att(report, verify=None):
    return AttemptView(0, "B", False, 0, 10, "moderate", report, verify, 100)


def test_new_stage():
    assert labels(legal_actions(obs(Stage.NEW), PUB)) == ["triage", "request_info"]
    assert labels(legal_actions(obs(Stage.NEW, info_requested=True), PUB)) == ["triage"]


def test_dispatch_ready_eligibility_and_defer():
    got = labels(legal_actions(obs(Stage.DISPATCH_READY), PUB))
    assert "dispatch(A)" not in got  # A is not electrical-eligible
    assert got == ["dispatch(B)", "dispatch(C)", "dispatch(D)", "escalate(B)", "escalate(C)", "escalate(D)", "defer"]


def test_urgent_only_escalate():
    got = labels(legal_actions(obs(Stage.DISPATCH_READY, reported_severity="urgent"), PUB))
    assert got == ["escalate(B)", "escalate(C)", "escalate(D)"]
    got = labels(legal_actions(obs(Stage.WORK_REPORTED, reported_severity="urgent", attempts=(att("needs_return"),)), PUB))
    assert got == ["escalate(B)", "escalate(C)", "escalate(D)"]


def test_attempt_limit_only_escalate_c():
    got = labels(legal_actions(obs(Stage.DISPATCH_READY, observed_failure_count=4), PUB))
    assert got == ["escalate(C)"]
    got = labels(legal_actions(obs(Stage.WORK_REPORTED, observed_failure_count=4, attempts=(att("complete"),)), PUB))
    assert got == ["close", "verify", "escalate(C)"]


def test_defer_requires_slack_and_count():
    assert "defer" not in labels(legal_actions(obs(Stage.DISPATCH_READY, sla_deadline_tick=1440), PUB))
    assert "defer" in labels(legal_actions(obs(Stage.DISPATCH_READY, sla_deadline_tick=1441), PUB))
    assert "defer" not in labels(legal_actions(obs(Stage.DISPATCH_READY, defer_count=2), PUB))


def test_work_reported_complete_vs_needs_return():
    c = labels(legal_actions(obs(Stage.WORK_REPORTED, attempts=(att("complete"),)), PUB))
    assert c[:2] == ["close", "verify"] and "redispatch(B)" in c and "escalate(C)" in c
    n = labels(legal_actions(obs(Stage.WORK_REPORTED, attempts=(att("needs_return"),)), PUB))
    assert "close" not in n and "verify" not in n and "redispatch(B)" in n


def test_verified_stages():
    assert labels(legal_actions(obs(Stage.VERIFIED_OK), PUB)) == ["close"]
    v = labels(legal_actions(obs(Stage.VERIFIED_FAIL), PUB))
    assert "close" not in v and "redispatch(D)" in v


@pytest.mark.parametrize("stage", [Stage.QUEUED, Stage.IN_PROGRESS, Stage.CLOSED, Stage.INFO_WAIT,
                                   Stage.DEFER_WAIT, Stage.VERIFY_PENDING])
def test_no_decision_at_non_decision_stage(stage):
    with pytest.raises(ValueError):
        legal_actions(obs(stage), PUB)


class IllegalPolicy:
    name = "ILLEGAL"

    def reset(self, *a):
        pass

    def act(self, observation, legal):
        a = legal[0]
        return Action(a.request_id, a.stage, ActionType.CLOSE, None, a.tick)  # close is never legal at NEW

    def observe_feedback(self, events):
        pass

    def diagnostics(self):
        return {}


def test_illegal_action_invalidates_run():
    cfg = small_cfg([{"time": {"warmup_days": 1}}])
    eng, out, _ = run_p0(cfg, policy=IllegalPolicy())
    assert out.status == "INVALID"
    assert out.validation_errors and out.validation_errors[0]["type"] == "illegal_action"


def test_engine_transitions_follow_table():
    allowed = {
        ("NEW", "triage"): "DISPATCH_READY", ("NEW", "request_info"): "INFO_WAIT",
        ("DISPATCH_READY", "dispatch"): "QUEUED", ("DISPATCH_READY", "escalate"): "QUEUED",
        ("DISPATCH_READY", "defer"): "DEFER_WAIT", ("WORK_REPORTED", "close"): "CLOSED",
        ("WORK_REPORTED", "verify"): "VERIFY_PENDING", ("WORK_REPORTED", "redispatch"): "QUEUED",
        ("WORK_REPORTED", "escalate"): "QUEUED", ("VERIFIED_OK", "close"): "CLOSED",
        ("VERIFIED_FAIL", "redispatch"): "QUEUED", ("VERIFIED_FAIL", "escalate"): "QUEUED",
    }
    _, out, _ = run_p0(small_cfg())
    assert out.status == "VALID"
    for a in out.action_records:
        assert (a["stage"], a["type"]) in allowed
