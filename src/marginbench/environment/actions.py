"""Legal actions (SPEC 7.2). Computed only from the policy observation and public config,
so legality can never reveal LATENT or EVALUATOR_ONLY state (SPEC 18.4)."""

from __future__ import annotations

from marginbench.config import PublicConfig
from marginbench.schemas import Action, ActionType, Observation, Stage

DAY = 1440


def _dispatch_like(obs: Observation, pub: PublicConfig, kind: ActionType) -> list[Action]:
    req = obs.request
    rid, st, t = req.request_id, req.stage, obs.tick
    eligible = [c for c in obs.contractors if req.category in c.eligible]
    if req.observed_failure_count >= pub.attempt_limit_failures:
        return [Action(rid, st, ActionType.ESCALATE, pub.escalation_contractor, t)]
    esc = [Action(rid, st, ActionType.ESCALATE, c.contractor_id, t) for c in eligible]
    if req.reported_severity == "urgent":
        return esc
    disp = [Action(rid, st, kind, c.contractor_id, t) for c in eligible]
    return disp + esc


def sla_slack_minutes(obs: Observation) -> float:
    req = obs.request
    if req.first_start_tick is not None:
        return float("inf")  # SLA already met or breached: no pending SLA exposure (DECISIONS D-11)
    if req.sla_breached:
        return float("-inf")
    if req.sla_deadline_tick is None:
        return float("inf")
    return float(req.sla_deadline_tick - obs.tick)


def legal_actions(obs: Observation, pub: PublicConfig) -> tuple[Action, ...]:
    req = obs.request
    rid, st, t = req.request_id, req.stage, obs.tick
    acts: list[Action] = []
    if st == Stage.NEW:
        acts.append(Action(rid, st, ActionType.TRIAGE, None, t))
        if not req.info_requested:
            acts.append(Action(rid, st, ActionType.REQUEST_INFO, None, t))
    elif st == Stage.DISPATCH_READY:
        acts.extend(_dispatch_like(obs, pub, ActionType.DISPATCH))
        if (
            req.observed_failure_count < pub.attempt_limit_failures
            and req.reported_severity != "urgent"
            and req.defer_count < pub.max_defers
            and sla_slack_minutes(obs) > DAY
        ):
            acts.append(Action(rid, st, ActionType.DEFER, None, t))
    elif st == Stage.WORK_REPORTED:
        last = req.attempts[-1].report if req.attempts else None
        if last == "complete":
            acts.append(Action(rid, st, ActionType.CLOSE, None, t))
            acts.append(Action(rid, st, ActionType.VERIFY, None, t))
        acts.extend(_dispatch_like(obs, pub, ActionType.REDISPATCH))
    elif st == Stage.VERIFIED_FAIL:
        acts.extend(_dispatch_like(obs, pub, ActionType.REDISPATCH))
    elif st == Stage.VERIFIED_OK:
        acts.append(Action(rid, st, ActionType.CLOSE, None, t))
    else:
        raise ValueError(f"no decision at stage {st}")
    acts.sort(key=Action.sort_key)
    if not acts:
        raise ValueError(f"empty legal action set for {rid} at {st}")
    return tuple(acts)


def match_legal(chosen: Action, legal: tuple[Action, ...]) -> Action | None:
    for a in legal:
        if (a.request_id, a.stage, a.type, a.contractor, a.tick) == (
            chosen.request_id, chosen.stage, chosen.type, chosen.contractor, chosen.tick
        ):
            return a
    return None
