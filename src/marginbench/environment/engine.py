"""Authoritative discrete-event simulator (SPEC 3-7).

The engine owns all mutable state. Policies are called with frozen observations built by
the allowlist serializer and never receive a reference to the engine.
"""

from __future__ import annotations

import dataclasses
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import numpy as np

from marginbench.config import Config, PublicConfig, public_config
from marginbench.economics.contracts import annual_fee_cents, daily_fee_cents
from marginbench.economics.ledger import Ledger
from marginbench.environment import callbacks as cbm
from marginbench.environment import contractors as ctm
from marginbench.environment import losses as lsm
from marginbench.environment import repairs as rpm
from marginbench.environment import retention as rtm
from marginbench.environment import sla as slm
from marginbench.environment import verification as vfm
from marginbench.environment.actions import legal_actions, match_legal
from marginbench.environment.arrivals import Opportunity, World
from marginbench.environment.events import PRIORITY, EventQueue, Scheduled
from marginbench.environment.observations import (
    contractor_view,
    observable_event,
    property_view,
    request_view,
)
from marginbench.environment.randomness import policy_mc_seed
from marginbench.environment.state import (
    AttemptRecord,
    ContractorState,
    ContractState,
    PropertyState,
    RequestState,
    TenantState,
)
from marginbench.hashing import StreamHasher
from marginbench.schemas import (
    Action,
    ActionType,
    EntryStatus,
    Event,
    IllegalActionError,
    ObservableEvent,
    Observation,
    Principal,
    Stage,
    make_data,
)

DAY = 1440


class ResourceLimitError(RuntimeError):
    pass


@dataclass(frozen=True)
class RunSpec:
    run_id: str
    horizon_days: int
    run_nonce: int
    mode: str = "eval"  # "eval" or "history"
    deploy_variant: bool = False
    collect_trace: bool = False
    max_events: int = 2_000_000


@dataclass
class RunOutput:
    run_id: str
    status: str
    events: list[Event]
    ledger: Ledger
    requests: dict[str, RequestState]
    contracts: dict[str, ContractState]
    properties: dict[str, PropertyState]
    contractors: dict[str, ContractorState]
    callback_ticks: dict[str, list[int]]
    action_records: list[dict[str, Any]]
    boundary: dict[str, Any]
    validation_errors: list[dict[str, Any]]
    event_hash: str
    ledger_hash: str
    decisions_by_policy: dict[str, int]
    wall_seconds: float
    contractor_prices: dict[str, float]
    policy_diagnostics: dict[str, Any] = field(default_factory=dict)


class Engine:
    def __init__(
        self,
        cfg: Config,
        world: World,
        spec: RunSpec,
        arm_policy: Any,
        p0_policy: Any,
    ) -> None:
        self.cfg = cfg
        self.world = world
        self.spec = spec
        self.arm = arm_policy
        self.p0 = p0_policy
        self.pub: PublicConfig = public_config(cfg)
        self.streams = world.streams
        self.end_tick = spec.horizon_days * DAY
        self.W = cfg.time.warmup_days
        self.decision_end = cfg.time.decision_end_day
        self.ledger = Ledger(spec.run_id)
        self.queue = EventQueue()
        self.events: list[Event] = []
        self.event_hasher = StreamHasher()
        self.next_event_id = 0
        self.validation_errors: list[dict[str, Any]] = []
        self.action_records: list[dict[str, Any]] = []
        self.feedback_buffer: list[ObservableEvent] = []
        self.feedback_cursor: dict[int, int] = {}
        self.decisions_by_policy: dict[str, int] = {}
        self.callback_ticks: dict[str, list[int]] = {}
        self.opportunities: dict[str, Opportunity] = {o.opportunity_id: o for o in world.opportunities}
        self._loss_u: dict[str, np.ndarray] = {}
        self._term_u: dict[str, np.ndarray] = {}
        self.at_risk: set[str] = set()

        self.properties: dict[str, PropertyState] = {}
        self.contracts: dict[str, ContractState] = {}
        for p in world.properties:
            self.properties[p.property_id] = PropertyState(
                property_id=p.property_id, owner_id=p.owner_id, contract_id=p.contract_id,
                unit_count=p.unit_count, risk=p.risk, condition=p.condition, condition_obs=p.condition_obs,
            )
            self.contracts[p.contract_id] = ContractState(
                contract_id=p.contract_id, property_id=p.property_id,
                annual_fee_cents=annual_fee_cents(cfg.fees.per_unit_month, p.unit_count),
            )
        self.contract_of = {p.property_id: p.contract_id for p in world.properties}
        self.tenants: dict[str, TenantState] = {
            t.tenant_id: TenantState(t.tenant_id, t.unit_id, t.property_id, t.report_propensity) for t in world.tenants
        }
        self.contractors: dict[str, ContractorState] = {}
        for c in world.contractors:
            self.contractors[c.contractor_id] = ContractorState(
                contractor_id=c.contractor_id, price_multiplier=c.price_multiplier, eligible=c.eligible,
                speed=c.speed, capacity=c.capacity, logit_success=c.logit_success,
                category_offsets=dict(c.category_offsets),
            )
        self.requests: dict[str, RequestState] = {}

    # ------------------------------------------------------------------ infrastructure
    def _new_id(self) -> int:
        eid = self.next_event_id
        self.next_event_id += 1
        return eid

    def _schedule(self, tick: int, typ: str, request_id: Optional[str] = None, **data: Any) -> None:
        self.queue.push(Scheduled(tick, PRIORITY[typ], self._new_id(), typ, request_id, data))

    def _log(self, typ: str, tick: int, priority: int, request_id: Optional[str] = None,
             property_id: Optional[str] = None, event_id: Optional[int] = None, **data: Any) -> Event:
        ev = Event(
            event_id=self._new_id() if event_id is None else event_id,
            tick=tick, priority=priority, type=typ, request_id=request_id, property_id=property_id,
            data=make_data(**data),
        )
        self.events.append(ev)
        self.event_hasher.add(ev.to_record())
        if len(self.events) > self.spec.max_events:
            raise ResourceLimitError("max events per replication exceeded")
        oe = observable_event(typ, tick, request_id, property_id, data)
        if oe is not None:
            self.feedback_buffer.append(oe)
        return ev

    def _post(self, ev: Event, principal: Principal, category: str, cents: int, contract_id: str,
              request_id: Optional[str] = None, action_id: Optional[str] = None,
              status: EntryStatus = EntryStatus.REALIZED) -> None:
        if cents == 0:
            return
        self.ledger.post(event_id=ev.event_id, tick=ev.tick, principal=principal, category=category,
                         amount_cents=cents, contract_id=contract_id, request_id=request_id,
                         action_id=action_id, status=status)

    def _cents(self, dollars: float) -> int:
        return int(round(dollars * 100))

    def _loss_uniform(self, rid: str, day: int) -> float:
        v = self._loss_u.get(rid)
        if v is None:
            v = self.streams.uniforms("severe_loss_day", rid, 0, self.cfg.time.generation_days)
            self._loss_u[rid] = v
        return float(v[day])

    def _term_uniform(self, kid: str, day: int) -> float:
        v = self._term_u.get(kid)
        if v is None:
            v = self.streams.uniforms("termination", kid, 0, self.cfg.time.generation_days)
            self._term_u[kid] = v
        return float(v[day])

    def _features(self, prop: PropertyState, day: int) -> dict[str, float]:
        return rtm.features(prop.callback_log, prop.breach_log, prop.loss_log, prop.spend_log, prop.unit_count, day)

    # ------------------------------------------------------------------ run
    def run(self) -> RunOutput:
        t0 = time.perf_counter()
        status = "VALID"
        try:
            self._schedule(0, "DAY_START", None, day=0)
            for o in self.world.opportunities:
                if o.tick < self.end_tick:
                    self._schedule(o.tick, "ARRIVAL", o.opportunity_id)
            while len(self.queue):
                item = self.queue.pop()
                if item.tick >= self.end_tick:
                    self.queue.push(item)
                    break
                self._handle(item)
        except IllegalActionError as exc:
            status = "INVALID"
            self.validation_errors.append({"type": "illegal_action", "detail": str(exc)})
        except ResourceLimitError as exc:
            status = "RESOURCE_LIMIT"
            self.validation_errors.append({"type": "resource_limit", "detail": str(exc)})
        boundary = self._boundary()
        diags: dict[str, Any] = {}
        for pol in {id(self.arm): self.arm, id(self.p0): self.p0}.values():
            if hasattr(pol, "diagnostics"):
                diags[getattr(pol, "name", "policy")] = pol.diagnostics()
        ledger_hasher = StreamHasher()
        for e in self.ledger.entries:
            ledger_hasher.add(e.to_record())
        return RunOutput(
            run_id=self.spec.run_id, status=status, events=self.events, ledger=self.ledger,
            requests=self.requests, contracts=self.contracts, properties=self.properties,
            contractors=self.contractors, callback_ticks=self.callback_ticks,
            action_records=self.action_records, boundary=boundary,
            validation_errors=self.validation_errors, event_hash=self.event_hasher.hexdigest(),
            ledger_hash=ledger_hasher.hexdigest(), decisions_by_policy=self.decisions_by_policy,
            wall_seconds=time.perf_counter() - t0,
            contractor_prices={c: s.price_multiplier for c, s in self.contractors.items()},
            policy_diagnostics=diags,
        )

    def _handle(self, it: Scheduled) -> None:
        h = getattr(self, "_on_" + it.type.lower())
        h(it)

    # ------------------------------------------------------------------ routing and decisions
    def _policy_for(self, req: RequestState, day: int) -> Any:
        if self.spec.mode == "history":
            return self.arm
        if day < self.W:
            return self.p0
        if day <= self.decision_end or self.spec.deploy_variant:
            return self.arm
        if req.cohort and req.first_closure_tick is None:
            return self.arm
        return self.p0

    def _start_preview(self, req: RequestState, c: ContractorState, tick: int) -> Optional[int]:
        if req.category not in c.eligible:
            return None
        if req.reopened_by_callback and not self.cfg.callbacks.consume_capacity:
            return ctm.overtime_start_tick(tick, self.cfg.contractors.escalation_delay_minutes, c.speed)
        return ctm.preview_start_tick(c.schedule, c.capacity, tick, self.cfg.contractors.base_lead_days[req.category], c.speed)

    def observation(self, req: RequestState, tick: int) -> Observation:
        day = tick // DAY
        prop = self.properties[req.property_id]
        k = self.contracts[prop.contract_id]
        esc_delay = self.cfg.contractors.escalation_delay_minutes
        cviews = tuple(
            contractor_view(c, tick, self._start_preview(req, c, tick), ctm.overtime_start_tick(tick, esc_delay, c.speed))
            for _, c in sorted(self.contractors.items())
        )
        return Observation(
            tick=tick,
            day=day,
            request=request_view(req),
            property=property_view(prop, k, self._features(prop, day)),
            contractors=cviews,
            tenant_complaint_count=self.tenants[req.tenant_id].complaint_count,
            mc_seed=policy_mc_seed(self.spec.run_nonce, req.request_id, req.decision_index),
        )

    def _decide(self, req: RequestState, tick: int, priority: int) -> None:
        if req.handed_over:
            return
        pol = self._policy_for(req, tick // DAY)
        obs = self.observation(req, tick)
        legal = legal_actions(obs, self.pub)
        cur = self.feedback_cursor.get(id(pol), 0)
        if cur < len(self.feedback_buffer):
            pol.observe_feedback(tuple(self.feedback_buffer[cur:]))
            self.feedback_cursor[id(pol)] = len(self.feedback_buffer)
        chosen = pol.act(obs, legal)
        match = match_legal(chosen, legal) if isinstance(chosen, Action) else None
        if match is None:
            self.validation_errors.append({
                "type": "illegal_action", "request_id": req.request_id, "tick": tick,
                "policy": getattr(pol, "name", "?"), "action": repr(chosen),
            })
            raise IllegalActionError(f"{getattr(pol, 'name', '?')} chose illegal action {chosen!r}")
        name = getattr(pol, "name", "?")
        self.decisions_by_policy[name] = self.decisions_by_policy.get(name, 0) + 1
        action_id = f"{req.request_id}#{req.decision_index}"
        act = dataclasses.replace(
            match, action_id=action_id, reason_code=str(chosen.reason_code or ""),
            estimated_value=chosen.estimated_value, estimated_risk=chosen.estimated_risk,
        )
        req.decision_index += 1
        extra: dict[str, Any] = {}
        prop_fn = getattr(pol, "last_propensity", None)
        if prop_fn is not None:
            extra["propensity"] = prop_fn
        ev = self._log(
            "ACTION", tick, priority, req.request_id, req.property_id,
            action_id=action_id, action_type=act.type.value, contractor=act.contractor, stage=act.stage.value,
            policy=name, reason_code=act.reason_code, estimated_value=act.estimated_value,
            estimated_risk=act.estimated_risk, n_legal=len(legal), **extra,
        )
        rec = {
            "action_id": action_id, "request_id": req.request_id, "tick": tick, "stage": act.stage.value,
            "type": act.type.value, "contractor": act.contractor, "reason_code": act.reason_code,
            "estimated_value": act.estimated_value, "estimated_risk": act.estimated_risk, "policy": name,
            "event_id": ev.event_id, "n_legal": len(legal),
        }
        rec.update(extra)
        self.action_records.append(rec)
        self._apply(req, act, ev, priority)

    def _apply(self, req: RequestState, a: Action, ev: Event, priority: int) -> None:
        cfg = self.cfg
        t = ev.tick
        kid = self.contract_of[req.property_id]
        rid = req.request_id
        if a.type == ActionType.TRIAGE:
            req.stage = Stage.DISPATCH_READY
            self._enter_dispatch_ready(req, t, priority)
        elif a.type == ActionType.REQUEST_INFO:
            self._post(ev, Principal.OPERATOR, "info_expense", -self._cents(cfg.costs.info), kid, rid, a.action_id)
            req.info_requested = True
            req.stage = Stage.INFO_WAIT
            self._schedule(t + cfg.obs.info_delay_days * DAY, "INFO_ARRIVES", rid)
        elif a.type in (ActionType.DISPATCH, ActionType.REDISPATCH, ActionType.ESCALATE):
            self._dispatch(req, a, ev, kid)
        elif a.type == ActionType.DEFER:
            req.defer_count += 1
            req.stage = Stage.DEFER_WAIT
            self._schedule(t + DAY, "DEFER_ELAPSES", rid)
        elif a.type == ActionType.VERIFY:
            self._post(ev, Principal.OPERATOR, "verification_expense", -self._cents(cfg.verify.cost), kid, rid, a.action_id)
            vidx = req.verification_index
            req.verification_index += 1
            req.stage = Stage.VERIFY_PENDING
            self._schedule(t + cfg.verify.delay_days * DAY, "VERIFY_RESULT", rid, vindex=vidx)
        elif a.type == ActionType.CLOSE:
            self._close(req, a, t)
        else:  # pragma: no cover
            raise IllegalActionError(f"unhandled action {a.type}")

    def _enter_dispatch_ready(self, req: RequestState, tick: int, priority: int) -> None:
        if req.sla_tier is None:
            req.sla_tier = req.reported_severity
            req.sla_deadline_tick = slm.sla_deadline(self.cfg, req.arrival_tick, req.sla_tier)
            self._schedule(max(req.sla_deadline_tick, tick), "SLA_CHECK", req.request_id)
        self._decide(req, tick, priority)

    def _dispatch(self, req: RequestState, a: Action, ev: Event, kid: str) -> None:
        cfg = self.cfg
        t = ev.tick
        rid = req.request_id
        c = self.contractors[a.contractor or ""]
        self._post(ev, Principal.OPERATOR, "dispatch_expense", -self._cents(cfg.costs.dispatch), kid, rid, a.action_id)
        escalated = a.type == ActionType.ESCALATE
        if escalated:
            self._post(ev, Principal.OPERATOR, "escalation_expense", -self._cents(cfg.costs.escalation), kid, rid, a.action_id)
            start = ctm.overtime_start_tick(t, cfg.contractors.escalation_delay_minutes, c.speed)
        elif req.reopened_by_callback and not cfg.callbacks.consume_capacity:
            start = ctm.overtime_start_tick(t, cfg.contractors.escalation_delay_minutes, c.speed)
        else:
            start = ctm.book_slot(c.schedule, c.capacity, t, cfg.contractors.base_lead_days[req.category], c.speed)
        c.pending_starts.append(start)
        j = req.attempt_index
        z = float(self.streams.gen("duration", rid, j).standard_normal())
        dur = rpm.job_duration_minutes(cfg, z)
        req.attempts.append(AttemptRecord(
            attempt_index=j, contractor=c.contractor_id, escalated=escalated, dispatch_tick=t,
            reported_severity_at_dispatch=req.reported_severity,
        ))
        req.attempt_index += 1
        req.stage = Stage.QUEUED
        self._schedule(start, "WORK_START", rid, attempt=j)
        self._schedule(start + dur, "WORK_COMPLETE", rid, attempt=j)

    def _close(self, req: RequestState, a: Action, t: int) -> None:
        unverified = a.stage == Stage.WORK_REPORTED
        req.stage = Stage.CLOSED
        req.last_close_unverified = unverified
        if req.attempts:
            req.attempts[-1].closed_tick = t
        if req.first_closure_tick is None:
            req.first_closure_tick = t
        rid = req.request_id
        if not req.physical_resolved:
            ep = req.failure_episode_index
            req.failure_episode_index += 1
            g = self.streams.gen("callback", rid, ep)
            u_occ = float(g.random())
            gam = float(g.gamma(self.cfg.callbacks.delay_gamma_shape, 1.0))
            rho = self.tenants[req.tenant_id].report_propensity
            p = cbm.callback_probability(self.cfg, rho, req.true_severity, unverified)
            if u_occ < p:
                cb_tick = t + cbm.callback_delay_minutes(self.cfg, gam)
                req.pending_true_callback_tick = cb_tick
                self._schedule(cb_tick, "CALLBACK", rid, kind="true")
        elif not req.benign_drawn:
            req.benign_drawn = True
            g = self.streams.gen("benign", rid, 0)
            u_occ, u_time = (float(x) for x in g.random(2))
            d = cbm.benign_repeat_delay(self.cfg, u_occ, u_time)
            if d is not None:
                self._schedule(t + d, "CALLBACK", rid, kind="benign")

    # ------------------------------------------------------------------ event handlers
    def _on_day_start(self, it: Scheduled) -> None:
        d = int(it.data["day"])
        cfg = self.cfg
        ev = self._log("DAY_START", it.tick, it.priority, event_id=it.event_id, day=d)
        # 1. effective terminations
        for kid in sorted(self.contracts):
            k = self.contracts[kid]
            if k.status == "NOTICE" and k.effective_day is not None and k.effective_day <= d:
                k.status = "TERMINATED"
                self._log("CONTRACT_TERMINATED", it.tick, it.priority, None, k.property_id, contract_id=kid, day=d)
                self._handover(k.property_id, it.tick, it.priority)
        # 2. fee accrual for day d (ACTIVE, or NOTICE before the effective date)
        for kid in sorted(self.contracts):
            k = self.contracts[kid]
            if k.status in ("ACTIVE", "NOTICE"):
                fee = daily_fee_cents(k.annual_fee_cents, d)
                k.booked_fee_cents += fee
                self._post(ev, Principal.OPERATOR, "fee_revenue", fee, kid, status=EntryStatus.ACCRUED)
        # 3. severe-loss hazard for day d-1
        if d >= 1:
            self._loss_checks(d - 1, it)
        # 4. termination hazard for day d
        for kid in sorted(self.contracts):
            k = self.contracts[kid]
            if k.status != "ACTIVE":
                continue
            prop = self.properties[k.property_id]
            h = rtm.hazard(cfg, self._features(prop, d))
            k.last_hazard = h
            if self._term_uniform(kid, d) < min(h, 1.0):
                k.status = "NOTICE"
                k.notice_day = d
                k.effective_day = d + cfg.retention.notice_days
                self._log("TERMINATION_NOTICE", it.tick, it.priority, None, k.property_id,
                          contract_id=kid, day=d, effective_day=k.effective_day, hazard=h)
        if d + 1 < self.spec.horizon_days:
            self._schedule((d + 1) * DAY, "DAY_START", None, day=d + 1)

    def _loss_checks(self, day: int, it: Scheduled) -> None:
        cfg = self.cfg
        for rid in sorted(self.at_risk):
            req = self.requests[rid]
            if req.physical_resolved or req.handed_over or req.had_severe_loss:
                self.at_risk.discard(rid)
                continue
            if req.arrival_tick // DAY > day:
                continue
            hz = cfg.loss_hazard(req.true_severity)
            if hz <= 0.0 or self._loss_uniform(rid, day) >= hz:
                continue
            z = float(self.streams.gen("loss_amount", rid, 0).standard_normal())
            amount = lsm.loss_amount_cents(cfg, req.true_severity, z)
            negligent = (req.stage == Stage.CLOSED and req.last_close_unverified) or req.sla_breached
            op, own = lsm.split_loss(cfg, amount, negligent)
            kid = self.contract_of[req.property_id]
            ev = self._log("SEVERE_LOSS", it.tick, it.priority, rid, req.property_id, day=day,
                           amount_cents=amount, negligent=negligent, operator_cents=op, owner_cents=own,
                           owner_visible_amount_cents=amount, true_severity=req.true_severity)
            self._post(ev, Principal.OWNER, "severe_loss", -own, kid, rid)
            self._post(ev, Principal.OPERATOR, "severe_loss", -op, kid, rid)
            req.had_severe_loss = True
            req.severe_loss_cents = amount
            self.properties[req.property_id].loss_log.append((day, 1.0))
            self.at_risk.discard(rid)

    def _handover(self, property_id: str, tick: int, priority: int) -> None:
        for rid in sorted(self.requests):
            req = self.requests[rid]
            if req.property_id == property_id and not req.handed_over:
                req.handed_over = True
                self.at_risk.discard(rid)
                self._log("HANDOVER", tick, priority, rid, property_id, stage=req.stage.value)

    def _on_arrival(self, it: Scheduled) -> None:
        o = self.opportunities[it.request_id or ""]
        kid = self.contract_of[o.property_id]
        if self.contracts[kid].status == "TERMINATED":
            self._log("OPPORTUNITY_UNSERVED", it.tick, it.priority, o.opportunity_id, o.property_id,
                      event_id=it.event_id)
            return
        day = o.tick // DAY
        req = RequestState(
            request_id=o.opportunity_id, property_id=o.property_id, tenant_id=o.tenant_id,
            category=o.category, arrival_tick=o.tick, reported_severity=o.reported_severity,
            true_severity=o.true_severity, cohort=self.W <= day <= self.decision_end,
        )
        self.requests[req.request_id] = req
        if self.cfg.loss_hazard(req.true_severity) > 0:
            self.at_risk.add(req.request_id)
        self.tenants[o.tenant_id].complaint_count += 1
        self._log("ARRIVAL", it.tick, it.priority, req.request_id, req.property_id, event_id=it.event_id,
                  category=o.category, reported_severity=o.reported_severity, true_severity=o.true_severity,
                  cohort=req.cohort)
        self._decide(req, it.tick, it.priority)

    def _live(self, it: Scheduled) -> Optional[RequestState]:
        req = self.requests.get(it.request_id or "")
        if req is None or req.handed_over:
            return None
        return req

    def _on_info_arrives(self, it: Scheduled) -> None:
        req = self._live(it)
        if req is None:
            return
        req.reported_severity = self.opportunities[req.request_id].info_severity
        req.stage = Stage.DISPATCH_READY
        self._log("INFO_ARRIVES", it.tick, it.priority, req.request_id, req.property_id, event_id=it.event_id,
                  reported_severity=req.reported_severity)
        self._enter_dispatch_ready(req, it.tick, it.priority)

    def _on_defer_elapses(self, it: Scheduled) -> None:
        req = self._live(it)
        if req is None:
            return
        req.stage = Stage.DISPATCH_READY
        self._log("DEFER_ELAPSES", it.tick, it.priority, req.request_id, req.property_id, event_id=it.event_id)
        self._enter_dispatch_ready(req, it.tick, it.priority)

    def _on_work_start(self, it: Scheduled) -> None:
        req = self._live(it)
        if req is None:
            return
        att = req.attempts[-1]
        assert att.attempt_index == it.data["attempt"]
        att.start_tick = it.tick
        c = self.contractors[att.contractor]
        if it.tick in c.pending_starts:
            c.pending_starts.remove(it.tick)
        req.stage = Stage.IN_PROGRESS
        if req.first_start_tick is None:
            req.first_start_tick = it.tick
        self._log("WORK_START", it.tick, it.priority, req.request_id, req.property_id, event_id=it.event_id,
                  contractor=att.contractor, attempt_index=att.attempt_index)

    def _on_work_complete(self, it: Scheduled) -> None:
        req = self._live(it)
        if req is None:
            return
        cfg = self.cfg
        att = req.attempts[-1]
        j = att.attempt_index
        assert j == it.data["attempt"]
        c = self.contractors[att.contractor]
        prop = self.properties[req.property_id]
        rid = req.request_id
        was_resolved = req.physical_resolved
        p = rpm.success_probability(cfg, c.logit_success, c.category_offsets[req.category], req.true_severity,
                                    prop.condition, j)
        u = float(self.streams.gen("repair", rid, j).random())
        success = rpm.repair_outcome(was_resolved, p, u)
        if success and not was_resolved:
            req.physical_resolved = True
            req.resolved_tick = it.tick
            self.at_risk.discard(rid)
        report = rpm.contractor_report(cfg, success, float(self.streams.gen("report", rid, j).random()))
        base = cfg.invoice.base[req.category]
        mult = cfg.invoice.severity_multiplier[att.reported_severity_at_dispatch]
        invoice = int(round(base * mult * c.price_multiplier * 100))
        att.report = report
        att.invoice_cents = invoice
        att.success = success
        kid = self.contract_of[req.property_id]
        ev = self._log("WORK_COMPLETE", it.tick, it.priority, rid, req.property_id, event_id=it.event_id,
                       contractor=att.contractor, attempt_index=j, report=report, invoice_cents=invoice,
                       success=success, p_success=p, price_multiplier=c.price_multiplier, category=req.category,
                       reported_severity_at_dispatch=att.reported_severity_at_dispatch)
        self._post(ev, Principal.OWNER, "repair_invoice", -invoice, kid, rid)
        prop.spend_log.append((it.tick // DAY, invoice / 100.0))
        if report == "needs_return":
            req.observed_failure_count += 1
        req.stage = Stage.WORK_REPORTED
        self._decide(req, it.tick, it.priority)

    def _on_verify_result(self, it: Scheduled) -> None:
        req = self._live(it)
        if req is None:
            return
        vidx = int(it.data["vindex"])
        u = float(self.streams.gen("verify", req.request_id, vidx).random())
        res = vfm.verification_result(self.cfg, req.physical_resolved, u)
        att = req.attempts[-1]
        att.verify_result = res
        c = self.contractors[att.contractor]
        if res == "ok":
            c.observed_ok += 1
            req.stage = Stage.VERIFIED_OK
            if req.first_verified_ok_tick is None:
                req.first_verified_ok_tick = it.tick
        else:
            c.observed_fail += 1
            req.observed_failure_count += 1
            req.stage = Stage.VERIFIED_FAIL
        self._log("VERIFY_RESULT", it.tick, it.priority, req.request_id, req.property_id, event_id=it.event_id,
                  result=res, vindex=vidx, physically_resolved=req.physical_resolved)
        self._decide(req, it.tick, it.priority)

    def _on_callback(self, it: Scheduled) -> None:
        req = self._live(it)
        if req is None:
            return
        assert req.stage == Stage.CLOSED, (req.request_id, req.stage)
        kind = it.data["kind"]
        kid = self.contract_of[req.property_id]
        ev = self._log("CALLBACK", it.tick, it.priority, req.request_id, req.property_id, event_id=it.event_id,
                       kind=kind)
        self._post(ev, Principal.OPERATOR, "callback_expense", -self._cents(self.cfg.costs.callback), kid, req.request_id)
        if kind == "true":
            req.pending_true_callback_tick = None
        req.observed_failure_count += 1
        req.callback_count += 1
        req.reopened_by_callback = True
        self.callback_ticks.setdefault(req.request_id, []).append(it.tick)
        self.properties[req.property_id].callback_log.append((it.tick // DAY, 1.0))
        self.tenants[req.tenant_id].complaint_count += 1
        if req.attempts:
            self.contractors[req.attempts[-1].contractor].observed_callbacks += 1
            if req.attempts[-1].callback_tick is None:
                req.attempts[-1].callback_tick = it.tick
        req.stage = Stage.DISPATCH_READY
        self._enter_dispatch_ready(req, it.tick, it.priority)

    def _on_sla_check(self, it: Scheduled) -> None:
        req = self._live(it)
        if req is None or req.sla_breached:
            return
        if req.first_start_tick is None:
            tier = req.sla_tier or req.reported_severity
            req.sla_breached = True
            kid = self.contract_of[req.property_id]
            credit = slm.sla_credit_cents(self.cfg, tier)
            ev = self._log("SLA_BREACH", it.tick, it.priority, req.request_id, req.property_id,
                           event_id=it.event_id, tier=tier, credit_cents=credit)
            self._post(ev, Principal.OPERATOR, "sla_credit_paid", -credit, kid, req.request_id)
            self._post(ev, Principal.OWNER, "sla_credit_received", credit, kid, req.request_id)
            self.properties[req.property_id].breach_log.append((it.tick // DAY, 1.0))

    # ------------------------------------------------------------------ boundary (SPEC 6.4)
    def _boundary(self) -> dict[str, Any]:
        open_reqs = [r for r in self.requests.values() if not r.handed_over and r.stage != Stage.CLOSED]
        unresolved = [r for r in self.requests.values() if not r.handed_over and not r.physical_resolved]
        pending_cb = [r for r in self.requests.values()
                      if not r.handed_over and r.pending_true_callback_tick is not None
                      and r.pending_true_callback_tick >= self.end_tick]
        for r in self.requests.values():
            r.unreported_failure = (
                r.stage == Stage.CLOSED and not r.physical_resolved and r.pending_true_callback_tick is None
                and not r.handed_over
            )
        notice = [k for k in self.contracts.values() if k.status == "NOTICE"]
        end_day = self.spec.horizon_days
        fees_until_effective = 0
        for k in notice:
            for d in range(end_day, k.effective_day or end_day):
                fees_until_effective += daily_fee_cents(k.annual_fee_cents, d)
        lost_next_year = sum(k.annual_fee_cents for k in self.contracts.values() if k.status in ("NOTICE", "TERMINATED"))
        return {
            "label": "ESTIMATES - excluded from J (SPEC 6.4)",
            "open_requests": len(open_reqs),
            "unresolved_latent_failures": len(unresolved),
            "unreported_failures": sum(1 for r in self.requests.values() if r.unreported_failure),
            "pending_callbacks_scheduled": len(pending_cb),
            "contracts_in_notice": len(notice),
            "contracts_terminated": sum(1 for k in self.contracts.values() if k.status == "TERMINATED"),
            "estimated_fees_to_accrue_in_notice_cents": fees_until_effective,
            "estimated_future_fees_at_risk_next_365d_cents": lost_next_year,
        }
