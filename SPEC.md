# MarginBench v1.0: Implementation Specification

A falsifiable synthetic benchmark for when optimizing an operational proxy changes long-horizon business value, in either direction.

Language: Python 3.11 or 3.12. Execution mode: one autonomous build session. Research class: synthetic, model-conditional policy evaluation.

---

## 0. Instructions to the implementing agent

You are the research engineer building MarginBench in an empty repository. Implement, test, run, audit and document the whole system in this document. Deliver working software and real experiment outputs. Stubs, pseudocode and placeholders do not count as delivery.

When this document gives a default, use it. When it is silent, make the smallest defensible choice, record it in `DECISIONS.md` with a one-line reason, and continue. Do not stop to ask questions.

### 0.1 Priorities, in strict order

1. Causal and mathematical correctness.
2. Information separation and matched policy comparison.
3. Correct accounting and attribution of every dollar.
4. Determinism and reproducibility.
5. Falsifiability and honest uncertainty.
6. Tests.
7. Complete executable workflows.
8. Charts, reports, provenance traces.
9. Speed.

A smaller correct system beats a larger invalid one.

### 0.2 Prohibitions

- Never hard-code or tune toward any policy winning or losing.
- Never give one feasible policy information another feasible policy lacks.
- Never let a feasible policy call the authoritative simulator, read latent state, or read the evaluation ledger.
- Never treat administrative closure as physical repair.
- Never treat an unobserved callback as proof of a successful repair.
- Never count tenant rent as operator revenue.
- Never book lost future fees as an expense when fee accrual already stops.
- Never modify policies, models, environment parameters, metric definitions, sample sizes or the primary comparison after the locked evaluation starts. Any change makes a new experiment version.
- Never describe local seeds as confidential or the evaluation as blind. It is open and preregistered (Section 12).
- Never call a value gap "regret" unless the comparator optimum is computed exactly.
- Never present an oracle as deployable.
- Never report a number in any document that is not traceable to a run artifact.
- Never modify or delete a frozen test (Section 18.1).
- Never call an LLM API. The benchmark needs no network access after dependency installation.

### 0.3 Scope tiers

Build in tier order. If you run out of budget, stop at a tier boundary with everything in completed tiers passing, and report status `PARTIAL` with the last completed tier.

- **Tier 1:** foundation, environment, ledger, information boundary, P0, P1, P3, estimator training, E0, E1, E2, statistics module, report generator.
- **Tier 2:** P2, P4, P5, preregistration, locked primary evaluation, E3, E4, E9, ablations.
- **Tier 3:** E5, E6, E7, E8, sensitivity design, P6 oracle diagnostic.

### 0.4 Definition of done

- Installs from a lockfile with documented commands.
- All tests pass, including frozen tests, with the frozen-test hash check passing.
- `marginbench smoke` succeeds.
- The preregistered primary evaluation ran from a clean committed tree.
- Every monetary figure in every report reconciles to ledger entries.
- Every run records code commit, config hash, seed manifest and metric-definition version.
- Results use the classifications in Section 14.6, including null and opposite results, without code changes.
- A self-contained HTML report and charts exist on disk.
- `marginbench reproduce` regenerates a run with identical canonical hashes.
- The README states what the results establish and what they do not.

---

## 1. Research question and claim scope

**Primary question.** When a decision policy that beats the current operating baseline on a declared operational proxy replaces that baseline, does long-horizon operator value go up, stay the same, or go down, and under which declared conditions?

**Mechanisms the system must be able to separate:**

1. Objective misalignment.
2. Partial observability.
3. Predictive-model error and misspecification.
4. Planning-horizon limits.
5. Measurement manipulation, where actions change what gets observed.
6. Policy-induced distribution change, where actions change future workload and state.
7. Delayed consequences and tail risk.
8. Economic contract structure.

**Evidence levels:**

- **Level 1, synthetic:** holds in one declared configuration. Example claim: "Under configuration X, P2 raised the proxy and lowered simulated operator contribution."
- **Level 2, model-family robustness:** holds across the declared sensitivity design and structural ablations. Claim this only if the results support it.
- **Level 3, external validation:** out of scope. No output may imply Level 3.

All default parameter values in this document are synthetic engineering fixtures. They are not industry estimates and must never be cited as market data.

---

## 2. Formal model and estimands

### 2.1 Notation

- S_t: latent state.
- O_t: observation.
- H_t = (O_0, A_0, ..., O_t): observable history.
- A_t: action.
- π: policy.
- θ: environment parameters.
- U: exogenous randomness.

The dynamics are:

```
O_t ~ Ω_θ(· | S_t)
A_t ~ π(· | H_t)
S_{t+1} = T_θ(S_t, A_t, U)
```

Feasible policies see only H_t.

### 2.2 Objectives

**Proxy.** `G(π; θ)` is the fixed scalar defined in Section 8, computed on the decision cohort at the proxy cutoff.

**Business value.**

```
J(π; θ) = E[ Σ_{d = d0}^{d0 + D + M − 1} δ^(d − d0) · c_d ]
```

- c_d is the operator's net cash contribution on day d.
- d0 is the first decision-window day.
- D is the decision-window length.
- M is the maturation length.
- δ = 1.10^(−1/365).

No terminal value is added. Obligations pending at the horizon are reported separately (Section 6.4).

### 2.3 Contrasts

For policies a and b on the same paired replications:

```
ΔJ(a, b) = J(a) − J(b)
ΔG(a, b) = G(a) − G(b)
```

A **proxy reversal** of a against b is ΔG(a, b) > 0 and ΔJ(a, b) < 0, established with the uncertainty rules in Section 14. This is an estimand. It is never assumed.

**Primary contrast:** a = P2 (proxy-planning) against b = P0 (operating baseline). This is the deployment decision a company actually faces: replacing its current process with an agent that scores better on the dashboard.

### 2.4 Value gap and regret

Report the value gap to the best evaluated feasible policy, labeled exactly "gap to best evaluated policy". Use the word regret only in the analytically solvable fixtures of Section 18.5, where the optimum is computed exactly.

---

## 3. Time structure

| Item | Value |
|---|---|
| Clock unit | Integer minutes. Day = 1440 ticks. Day 0 is Jan 1 of a synthetic year. |
| Warm-up | Days 0 to 29 (W = 30). **P0 makes every decision for every policy arm.** Warm-up is therefore identical across arms within a replication, and every arm starts the decision window from the same state. |
| Decision window | Days 30 to 119 (D = 90). The policy under test makes all decisions on all requests: cohort requests, callbacks on pre-window requests, everything. |
| Cohort ownership | The policy under test keeps deciding each cohort request until that request's **first administrative closure**, even after day 119. This keeps G a measure of the tested policy alone. |
| Continuation and maturation | Days 120 to 299 (M = 180). **P0 makes every other decision** (standardized continuation): non-cohort requests, and cohort requests after their first closure, including their callbacks. Differences between arms in this window are caused by state the decision window left behind. |
| Decision cohort | Requests whose original arrival falls in the decision window. Callbacks link to their original request and are never new cohort members. |
| Proxy cutoff | End of day 133 (decision window end + 14 days). |
| Business-value window | Days 30 to 299, discounted to day 30. |
| Deployment variant | Secondary experiment E-DEPLOY: the policy under test keeps deciding through maturation. Report as secondary only. |

**Horizon sensitivity:** M ∈ {90, 180, 275}. At M = 275 the business-value window is 365 days. Run with the same seeds in E6.

**Arrival horizon:** arrivals are always generated for days 0 to W + D + M − 1 of the run in question. History portfolios (Section 10.1) generate days 0 to 364.

---

## 4. Entities and visibility

Every state field carries exactly one visibility class: `PUBLIC`, `OBSERVABLE_AFTER_EVENT`, `LATENT` or `EVALUATOR_ONLY`.

Policy observations are built by an allowlist serializer. Any field that is not explicitly allowlisted fails validation and is never forwarded.

### 4.1 Property (20 per portfolio)

| Field | Visibility | Notes |
|---|---|---|
| property_id, owner_id, contract_id, unit_count = 10 | PUBLIC | |
| risk factor r_p | LATENT | Lognormal, mean 1, log-sd 0.3 |
| condition q_p | LATENT | Beta(5, 2) |
| condition grade q_obs | PUBLIC | q_p + N(0, 0.1), clipped to [0, 1] |

### 4.2 Tenant (one per unit, 200 per portfolio)

| Field | Visibility | Notes |
|---|---|---|
| tenant_id, unit_id, property_id | PUBLIC | |
| reporting propensity ρ_t | LATENT | Beta(8, 2) |
| known complaint count | OBSERVABLE_AFTER_EVENT | |

Tenants do not move out in v1. This is a declared limitation.

### 4.3 Contractor (4 per portfolio)

| Field | Visibility | Notes |
|---|---|---|
| contractor_id | PUBLIC | |
| quoted price multiplier | PUBLIC | |
| eligible categories | PUBLIC | |
| published speed factor | PUBLIC | |
| daily capacity | PUBLIC | |
| current queue length | PUBLIC | |
| true success base and category offsets | LATENT | |
| historical observed outcome counts | OBSERVABLE_AFTER_EVENT | Only what observable events revealed |

### 4.4 Request

| Field | Visibility | Notes |
|---|---|---|
| request_id, property_id, tenant_id, category, arrival tick | PUBLIC | |
| reported severity | PUBLIC | |
| true severity | LATENT | |
| physical_resolved | LATENT | |
| lifecycle stage | OBSERVABLE_AFTER_EVENT | |
| attempt_index | OBSERVABLE_AFTER_EVENT | Number of prior dispatch or escalation jobs. A reopen does not increment it. |
| observed failure count | OBSERVABLE_AFTER_EVENT | Count of needs_return reports, VERIFIED_FAIL results and callbacks |
| contractor invoices | OBSERVABLE_AFTER_EVENT | Priced on reported severity at dispatch (Section 5.12) |
| contractor report | OBSERVABLE_AFTER_EVENT | |
| verification result | OBSERVABLE_AFTER_EVENT | |
| callback links | OBSERVABLE_AFTER_EVENT | |
| unreported-failure flag | EVALUATOR_ONLY | |
| severe-loss records | EVALUATOR_ONLY | Until the event occurs, then the owner-visible part is OBSERVABLE_AFTER_EVENT |

### 4.5 Management contract (one per property)

| Field | Visibility | Notes |
|---|---|---|
| fee terms, cost-allocation rules, service-credit rules | PUBLIC | |
| status, effective dates | OBSERVABLE_AFTER_EVENT | |
| termination hazard state | LATENT | |

Contracts lost in v1 are not replaced. The portfolio can only shrink. This is a declared limitation.

Events, observations, actions and ledger entries are immutable records (frozen Pydantic models or frozen dataclasses). Only the engine owns mutable state.

---

## 5. Mechanisms and default parameters

Every value below lives in `configs/default.yaml`, is validated by schema, is included in the run manifest, and is labeled synthetic in `ASSUMPTIONS.md`. Every causal mechanism has a zero-effect setting for ablation.

### 5.1 Exogenous arrivals (policy-independent, pre-generated per replication)

The arrival rate per unit-day for category k is:

```
λ_k(d) = 0.012 × share_k × r_p × s_k(d)
```

- share = plumbing 0.35, electrical 0.15, hvac 0.20, general 0.30.
- s_k = 1 for all categories except hvac, where s_hvac(d) = 1 + 0.5·cos(2π(d − 196)/365).

Generate every arrival opportunity for the run's full horizon (Section 3) before the run starts, with a stable ID and latent attributes. Every policy arm in a replication sees the identical opportunity list.

Mechanism toggles:

- `arrivals.seasonal`: on/off.
- `arrivals.heterogeneous`: when off, r_p = 1.

### 5.2 True severity by category

Probabilities are (minor, moderate, urgent):

| Category | Minor | Moderate | Urgent |
|---|---|---|---|
| Plumbing | 0.50 | 0.40 | 0.10 |
| Electrical | 0.45 | 0.40 | 0.15 |
| HVAC | 0.45 | 0.45 | 0.10 |
| General | 0.65 | 0.32 | 0.03 |

### 5.3 Observation model

- Reported severity equals true severity with probability `obs.severity_accuracy` = 0.80.
- Otherwise it is an adjacent class, chosen uniformly when two adjacent classes exist.
- The action `request_info` costs 1 day and raises accuracy for that request to 0.95. It resamples the report using a new keyed draw.
- `obs.perfect` ablation: accuracy 1.0, q_obs = q_p.

### 5.4 Contractors

Fixture means:

| ID | Price mult. | Base success s_c | Speed | Capacity (jobs/day) | Eligible |
|---|---|---|---|---|---|
| A | 0.75 | 0.68 | 0.8 | 3 | all except electrical |
| B | 1.00 | 0.82 | 1.0 | 3 | all |
| C | 1.35 | 0.93 | 1.0 | 2 | all |
| D | 0.95 | 0.70 | 1.5 | 4 | all |

**Per-replication perturbation:**

- logit(s_c) gets N(0, 0.2).
- Price gets ×(1 + N(0, 0.05)).
- Category offsets a_{c,k} ~ N(0, 0.3), drawn once per replication per (contractor, category).

**Declared assumption, to be written in `ASSUMPTIONS.md`:** the default world contains one fast and unreliable contractor (D). The sensitivity design (Section 15) varies speed-quality correlation from −0.6 to +0.6, including worlds where speed predicts quality. E1 is a world where proxy and value are built to align.

**Lead time.** With no queue, the earliest start day is dispatch day plus ceil(L_k / speed_c) days. Base lead L_k = general 2.0, plumbing 1.5, electrical 2.0, hvac 2.5.

**Capacity.** Effective capacity is max(1, floor(multiplier × capacity)). A job consumes one unit of the contractor's capacity on its start day. The job is scheduled once, at dispatch, into the earliest day at or after its earliest start day that has free capacity. Later jobs never bump scheduled jobs. Slots within a day are filled in scheduling order. The start time is 08:00 + 120 × (slot mod 8) minutes on day (earliest day + floor(slot / 8)), so the unlimited-capacity ablation never runs past midnight.

**Job duration.** Lognormal with median 120 minutes, log-sd 0.4. The completion event fires at start plus duration.

**Escalation.** The job starts at dispatch tick + 360 minutes / speed_c, uses overtime, and does not consume capacity. Operator pays $35.

Ablations:

- `contractors.unlimited_capacity`.
- `contractors.identical_quality`: every s_c = 0.82 and every offset = 0.
- `contractors.identical_price`: every multiplier = 1.0.
- `callbacks.consume_capacity` = false: callback re-dispatch is treated as escalation-free overtime, so callbacks do not consume capacity.

### 5.5 Repair outcome

For attempt j = attempt_index (0-indexed) by contractor c on a physically unresolved request (an attempt on an already-resolved request is a success):

```
logit p = logit(s_c) + a_{c,k} + b_sev + 1.0·(q_p − 0.7) − 0.4·j
```

- b_sev: minor +0.5, moderate 0, urgent −0.5.
- The result is physical success when u < p, where u is the keyed uniform from Section 11.
- After a success, physical_resolved stays true.

### 5.6 Contractor report

- On success: reports `complete` with probability 0.98, otherwise `needs_return`.
- On failure: reports `complete` with probability 0.80 (false completion), otherwise `needs_return`.

### 5.7 Verification

- Inspection happens 1 day after the request.
- Operator cost: $18.
- Sensitivity (detects an unresolved repair): 0.90.
- Specificity (passes a resolved repair): 0.95.
- Ablation `verify.perfect`: both set to 1.0.

### 5.8 Callbacks and reporting

When a request is closed or accepted while physically unresolved, the tenant eventually reports it with probability:

```
ρ_t × m_sev × m_close
```

- m_sev: minor 0.55, moderate 0.80, urgent 0.97.
- m_close = 0.85 if the request was administratively closed without verification, otherwise 1.0.
- Ablation `report.no_suppression` sets m_close = 1.0.

**Report delay:** Gamma(shape 2, scale 4 days).

**Callback effects:**

- The request reopens with attempt count + 1.
- Operator callback-handling cost: $20.
- The callback is owner-visible.
- Unreported failures stay latent, and the evaluator counts them.

**Benign repeat.** A physically resolved, closed request generates a spurious repeat contact within 30 days with probability 0.03 (uniform timing). The operator pays the $20 handling cost, the request reopens, and it is owner-visible as a callback. The next attempt on it is a success under Section 5.5 and is billed normally.

Ablation `callbacks.off`: tenants never report, and benign repeats are off.

### 5.9 Service levels and credits

**SLA target** (time from arrival to first work start), tiered by the request's **reported** severity at the time of its first dispatch decision:

- Urgent: 24 hours.
- Moderate: 72 hours.
- Minor: 7 days.

Each breach is one event, at most one per request. The operator pays the owner a credit of $40 for urgent and $15 for moderate. Minor breaches carry no credit. Breaches are owner-visible.

### 5.10 Severe loss

While a request is physically unresolved, from arrival onward, it carries a daily hazard of 0.004 if urgent and 0.0005 if moderate. Draw against the keyed uniform per (request, day). At most one severe loss per request.

**Amount:** lognormal with median $6,000 (urgent) or $2,500 (moderate), log-sd 1.0.

**Payer:** the owner, except that the operator bears a 25% share when either of these was true at loss time:

1. The request was administratively closed without verification.
2. The request had an SLA breach.

The rule is configurable via `loss.operator_negligence_share`.

The loss is owner-visible.

Ablation `loss.off`.

### 5.11 Owner retention

Each active contract has a daily termination hazard:

```
h = h0 · exp(β_cb·CB90 + β_br·BR90 + β_sl·SL365 + β_oc·OC90)
```

- h0 = −ln(1 − 0.06) / 365.
- CB90: callbacks per unit at the property over the trailing 90 days.
- BR90: SLA breaches at the property over the trailing 90 days.
- SL365: severe losses at the property over the trailing 365 days.
- OC90: owner repair spend per unit over the trailing 90 days, divided by $100.
- Defaults: β_cb = 2.0, β_br = 0.10, β_sl = 0.7, β_oc = 0.15.

Termination happens when the keyed uniform for (contract, day) is less than min(h, 1). The effective date is 30 days later, and fees accrue until the effective date.

**Mandatory null scenario `retention_null`:** every β = 0, so h = h0.

### 5.12 Fees and operator costs

**Fees:** $120 per unit-month, accrued daily as 120 × 12 / 365 per unit on active contracts. Accrual is calculated in exact rational cents, with the remainder carried forward per contract so the total over 365 days equals exactly 12 × 120 × units.

**Operator costs:**

| Item | Cost |
|---|---|
| Dispatch, per attempt including escalation | $12 |
| Verification | $18 |
| Callback handling | $20 |
| Escalation surcharge | $35 |
| `request_info` | $6 |
| SLA credits | Section 5.9 |
| Operator share of severe loss | Section 5.10 |

**Owner costs:**

- Contractor invoice per attempt, including failed attempts: base_k × severity multiplier × price_c, using the **reported** severity at dispatch. Invoices are OBSERVABLE_AFTER_EVENT.
- base_k: general $120, plumbing $240, electrical $280, hvac $350.
- Severity multiplier: minor 0.7, moderate 1.0, urgent 1.8.
- The owner's share of severe losses.
- SLA credits received, as a positive amount for the owner.

### 5.13 Attempt limit

When the observed failure count reaches 4, the only legal dispatch-stage action is escalation to contractor C, which is all-eligible. The rule uses only observable failures, so legality never reveals latent outcomes.

---

## 6. Ledger and economics

### 6.1 Entries

The ledger is append-only. Amounts are integer cents. Each entry has:

- entry_id, run_id, event_id, tick
- principal ∈ {OPERATOR, OWNER, TENANT, CONTRACTOR, THIRD_PARTY}
- category
- signed amount_cents
- request_id (optional), contract_id, action_id (optional)
- status ∈ {REALIZED, ACCRUED}
- reversal_of (optional)

Estimated exposures are stored in a separate file and table. They never enter the ledger.

### 6.2 Categories

- fee_revenue
- dispatch_expense
- verification_expense
- callback_expense
- escalation_expense
- info_expense
- sla_credit_paid (operator) / sla_credit_received (owner)
- repair_invoice (owner)
- severe_loss (split by principal)

### 6.3 Operator contribution

c_d is the sum of OPERATOR entries on day d. Discount once per day-total in floating point, then round the window total to cents. Never round individual discounted entries.

### 6.4 Boundary reporting (separate from J)

At the horizon end, report:

- open requests and unresolved latent failures
- pending callbacks already scheduled
- contracts in their notice period
- estimated future fees at risk

All of these are labeled as estimates and kept out of J.

### 6.5 Reconciliation

The run fails `INVALID` on any of:

- a duplicate entry
- an entry without a valid triggering event
- a payer misattribution
- fee accrual on an inactive contract
- a pending item recorded as realized
- per-principal totals that disagree with the event-derived recomputation

---

## 7. Workflow and actions

### 7.1 Transition table (single source of truth)

Implement exactly this table. Any transition not listed is illegal. CLOSED is an administrative state only. physical_resolved changes only through repair outcomes.

| From | Trigger | To |
|---|---|---|
| NEW | action `triage` (accepts the reported severity, no cost) | DISPATCH_READY |
| NEW | action `request_info` | INFO_WAIT |
| INFO_WAIT | event: info arrives after 1 day, reported severity resampled | DISPATCH_READY |
| DISPATCH_READY | action `dispatch(c)` or `escalate(c)` | QUEUED |
| DISPATCH_READY | action `defer` | DEFER_WAIT |
| DEFER_WAIT | event: 1 day elapses | DISPATCH_READY |
| QUEUED | event: work starts | IN_PROGRESS |
| IN_PROGRESS | event: work completes, report generated | WORK_REPORTED |
| WORK_REPORTED (complete) | action `close` | CLOSED |
| WORK_REPORTED (complete) | action `verify` | VERIFY_PENDING |
| WORK_REPORTED (any) | action `redispatch(c)` or `escalate(c)` | QUEUED |
| VERIFY_PENDING | event: result arrives | VERIFIED_OK or VERIFIED_FAIL |
| VERIFIED_OK | action `close` | CLOSED |
| VERIFIED_FAIL | action `redispatch(c)` or `escalate(c)` | QUEUED |
| CLOSED | event: callback (true or benign) | DISPATCH_READY |

attempt_index increments by 1 each time the request enters QUEUED. A callback does not increment it.

### 7.2 Decision points and legal actions

| Stage | Legal actions | Constraints |
|---|---|---|
| NEW | `triage`, `request_info` | `request_info` at most once per request |
| DISPATCH_READY | `dispatch(c)`, `escalate(c)`, `defer` | c must be eligible. If reported urgent, only `escalate(c)` is legal. `defer` is legal only if SLA slack exceeds 1 day and defer count < 2. If observed failure count ≥ 4, only `escalate(C)`. |
| WORK_REPORTED, complete | `close`, `verify`, `redispatch(c)`, `escalate(c)` | |
| WORK_REPORTED, needs_return | `redispatch(c)`, `escalate(c)` | |
| VERIFIED_FAIL | `redispatch(c)`, `escalate(c)` | |
| VERIFIED_OK | `close` | |

The reported-urgent and failure-count constraints apply to `redispatch` as well: for a reported-urgent request, `redispatch` is illegal and only `escalate(c)` is legal.

### 7.3 Action and decision records

- Each action carries: action_id, request_id, tick, stage, type, contractor (optional), reason_code, estimated_value (optional), estimated_risk (optional). Reason codes are policy claims, not explanations.
- Illegal actions raise a typed error. They are logged to `validation.json`, and the run is INVALID.
- Decisions are instantaneous at event time, processed in event order.

---

## 8. Proxy definition (`proxy_v1`, frozen)

Let N be the number of decision-cohort requests. At the proxy cutoff:

```
G = CR − 0.5 · (OPEX / N) / 25
```

**CR (closure rate):** the fraction of cohort requests whose first administrative closure happened by the cohort-relative closure target:

- Urgent: 2 days from arrival.
- Moderate: 5 days.
- Minor: 10 days.

Reopens do not reduce CR. This matches a common first-closure dashboard definition, and it is declared in `ASSUMPTIONS.md`.

**OPEX:** operator expense attributed to cohort requests through the cutoff. This covers dispatch, verification, callback, escalation, info and SLA credits. It excludes severe-loss shares, which are rare and lagged and do not appear on operational dashboards.

**Severity tiers** in CR use reported severity, since that is what the dashboard sees.

**N = 0:** G is `UNDEFINED`, never 0.

**Also report, never as the proxy:**

- verified resolution rate
- true resolution rate (EVALUATOR_ONLY)
- callback rate
- reopen rate
- mean and median time to closure and to verified resolution
- backlog and backlog age

---

## 9. Policies

All feasible policies:

- implement the Protocol below
- receive identical observation schemas and action sets
- use the same frozen estimator M (Section 10)

```python
class Policy(Protocol):
    name: str
    def reset(self, public_config: PublicConfig, estimator: FrozenEstimator,
              initial_observation: Observation) -> None: ...
    def act(self, observation: Observation,
            legal_actions: tuple[Action, ...]) -> Action: ...
    def observe_feedback(self, events: tuple[ObservableEvent, ...]) -> None: ...
    def diagnostics(self) -> dict[str, object]: ...
```

Isolation is an in-process software contract. Policies receive deep-copied frozen observations and never hold a reference to the engine. Document that this is not a security sandbox. Do not build a subprocess or container isolation layer in v1.

### 9.1 Action valuation

Used by P1 through P5.

For each legal action a, simulate the **request-level future** of this request K times. Each sample uses M's estimated parameters through a policy-side model implemented in `policies/internal_model.py`. That module must not import `environment/`.

The sample covers:

- lead times from observed queues and published speed
- repair success from p̂
- false completion and verification outcomes from estimated rates
- callback reporting from p̂_report
- SLA breach
- severe-loss hazard from the estimated hazard
- follow-on decisions for this request, made by the **fixed rollout rule**: P0's decision rule (Section 9.2) evaluated with M's estimates. There is no nested sampling. Every policy uses the same rollout rule, so compute stays matched.

Samples use common seeds across candidate actions (Section 11).

**Scoring.** Q(a) is the mean sampled objective over the horizon H_plan days from now:

- **Myopic** (H_plan = 0): count only consequences occurring before this request's next decision point.
- **Planning:** H_plan = 60 days.

**Objectives:**

- **Proxy objective, per request:** +1 if the request's first closure lands within its closure target and within the horizon, minus 0.5 × (operator cost incurred within horizon) / 25.
- **Economic objective:** Q_econ = the sum of **signed** operator cash flows within the horizon (costs are negative: dispatch, verify, callback, escalation, info, credits, estimated operator share of severe loss) minus the retention term (a positive number representing expected fee loss).

**Retention term.** For each sampled owner-visible event x at time t within the horizon:

```
increment = ĥ_now · (exp(β̂_x · w_x) − 1) · min(W_x, T_rem) · F_c · T_rem / 2
```

- w_x is the event's contribution to its trailing feature. For example, w = 1/units for a callback in CB90.
- W_x is the event's window: 90 days, or 365 for severe loss.
- T_rem is the days remaining until the end of the planning horizon.
- F_c is the contract's daily fee.

This first-order approximation is declared in `DECISIONS.md` and is identical across all economic policies.

**Congestion** enters only through observed queues and lead times. There is no shadow price on other requests' delays. Declared limitation.

**Matched compute:** K = 32 for every planning policy. Myopic policies use the same K with H_plan = 0. Ties break by action sort key. Record counts of samples, decisions and wall time per policy.

### 9.2 Policy definitions

**P0, operating baseline (deterministic rules):**

- triage as reported, never request info, never defer
- urgent: `escalate(C)`
- otherwise: dispatch to the lowest-price eligible contractor whose estimated success p̂ ≥ 0.75 and whose expected start meets SLA; ties go to the lower contractor_id; if none qualifies, the highest-p̂ eligible contractor
- **source of p̂:** during history generation (Section 10.1), before M exists, P0 uses the public prior p̂ = 0.80 for every contractor. With equal p̂, the rule reduces to "cheapest eligible contractor that meets SLA". After M is frozen, P0 uses M's p̂. Document both modes in `DECISIONS.md`.
- at WORK_REPORTED complete: verify if reported severity is moderate, otherwise close
- `needs_return` or VERIFIED_FAIL: redispatch with the same rule, excluding the contractor that just failed if any alternative exists

P0 is the primary comparator.

**The other policies:**

- **P1, proxy-myopic:** proxy objective, H_plan = 0.
- **P2, proxy-planning:** proxy objective, H_plan = 60.
- **P3, economic-myopic:** economic objective, H_plan = 0.
- **P4, economic-planning:** economic objective, H_plan = 60.
- **P5, constrained economic-planning:** P4, restricted to legal actions whose estimates satisfy:
  - P̂(severe loss on this request within horizon) ≤ max(0.002, R_min + 0.0005), where R_min is the lowest estimated severe-loss probability among the legal actions. The constraint is therefore relative and always satisfiable for at least one action.
  - P̂(SLA breach) ≤ max(0.10, B_min + 0.02), where B_min is defined the same way.
  - for `close`: P̂(physically unresolved | history) ≤ 0.15

  If no legal action satisfies all constraints, use the fallback, which always picks a legal action:
  - at WORK_REPORTED complete: `verify`
  - at VERIFIED_OK: `close`
  - wherever `redispatch` or `dispatch` is legal: the highest-p̂ eligible contractor
  - otherwise: `escalate` with the highest-p̂ eligible contractor

  Every fallback is recorded in diagnostics.
- **P6, oracle (Tier 3, default off):** P4 with true parameters and latent state. Every artifact and chart labels it `NON-DEPLOYABLE DIAGNOSTIC`. It is excluded from "best evaluated policy" and from all confirmatory comparisons.

### 9.3 Matched pairs

The pairs are (P1, P3), (P2, P4) and (P4, P5). Within each pair, these are identical:

- estimator
- H_plan and K
- sample seeds
- action set

Only the objective or the constraint differs.

---

## 10. Estimator M (shared, frozen)

### 10.1 Historical data

| Partition | Size | Use |
|---|---|---|
| Training | 60 portfolios × 365 days | Fit models |
| Calibration | 20 portfolios × 365 days | Regularization and calibration |

- **Behavior policy:** at each decision, P0's action with probability 0.7, otherwise uniform over legal actions. Propensities are logged.
- **Recorded data:** only observable events, actions, propensities, censoring flags and observation delays.

### 10.2 Models

All models are scikit-learn or closed-form, with regularization chosen on calibration.

- **Success p̂(c, k, reported sev, attempt index, q_obs):** L2 logistic regression. The label is a success indicator observable only through verification or a callback. Use only attempts matured at least 60 days before the history cutoff. Unverified attempts with no callback by then are **excluded**, not labeled as successes. Document the selection effect.
- **False-completion rate and verification sensitivity/specificity:** empirical rates from verified cases, with Beta(1, 1) shrinkage.
- **Callback model p̂_report(reported sev, closed-unverified):** logistic regression on matured failures detected by verification, with censoring documented.
- **Report delay:** fitted Gamma.
- **Lead time:** empirical per (contractor, category) plus observed queue.
- **Severe-loss hazard:** per-day Poisson rate by reported severity from observed events, with Gamma(1, 1000) shrinkage.
- **Termination hazard:** Poisson GLM on contract-days with the four trailing features plus an offset, L2-regularized. Report coefficients with standard errors.

### 10.3 Freezing and auditing

- Freeze all parameters into `models/estimator_v1.json`, hash the file, and record the hash in every run manifest. Never refit on evaluation data.
- **Audit outputs:** Brier score and calibration curve on calibration data for each binary model, sample sizes, censoring fractions, per-category error, and coefficient-vs-truth comparison (an evaluator-side diagnostic only).

**Sensitivity design:** each design point retrains M on 20 training portfolios generated under that point's parameters (Section 15). **E8** deliberately keeps M trained on the default world.

---

## 11. Randomness and coupling

**Stream key:**

```
SHA-256(f"{sim_version}|{partition}|{master_seed}|{replication}|{mechanism}|{entity_id}|{index}")
```

Take the first 8 bytes as an unsigned int to seed `np.random.Generator(PCG64DXSM(seed))`. Use one generator per (mechanism, entity), consumed in entity-local index order.

- Never use Python's `hash()`.
- Never use a global RNG.
- Pin the NumPy version.

| Mechanism | Key | Coupling across policy arms |
|---|---|---|
| Arrivals, latent request attributes | (replication, opportunity_id) | Identical |
| Property, tenant, contractor attributes | (replication, entity_id) | Identical |
| Repair success uniform | (request_id, attempt_index) | Shared uniform, so contractor choice is monotone-coupled |
| Contractor report | (request_id, attempt_index) | Shared |
| Job duration | (request_id, attempt_index) | Shared |
| Verification noise | (request_id, verification_index) | Shared |
| Callback occurrence, delay | (request_id, failure_episode_index) | Shared |
| Benign repeat | (request_id) | Shared |
| Severe loss occurrence | (request_id, day) | Shared |
| Severe loss amount | (request_id, loss_index) | Shared |
| Termination | (contract_id, day) | Shared |
| Info-request resample | (request_id, "info") | Shared |
| Policy internal Monte Carlo | Separate derivation, see below | Shared across policies |

**Policy Monte Carlo seeds.** For each decision, the runner hands the policy one integer:

```
SHA-256(f"policy-mc|{POLICY_SALT}|{run_nonce}|{request_id}|{decision_index}")
```

- POLICY_SALT is a constant distinct from every environment key component.
- run_nonce is a per-replication random value, unrelated to master_seed.
- The policy expands the integer into K samples.

master_seed, replication index, partition and sim_version never appear in PublicConfig, observations or feedback. A boundary test asserts that none of them can be recovered from anything passed to a policy. No policy name appears in the key, so matched policies share samples.

Endogenous events can still differ between arms because actions differ. That is intended. Document the coupling in `DECISIONS.md`.

---

## 12. Partitions and preregistration

**Partitions** are the partition labels in the stream key: `train`, `calib`, `dev`, `eval`, `stress`, `sens`, `pilot`. Master seeds are integers per partition.

**Development:** use only `dev` for development and debugging.

**Preregistration, before the locked evaluation:**

1. Run the power analysis (Section 14.5) on `calib` to set n_eval.
2. Write `configs/plan.yaml`, the machine-readable plan, covering:
   - primary and secondary contrasts, estimands, proxy and metric definition versions
   - materiality m, α, interval method, n per experiment
   - scenario configs, estimator hash, policy versions, sensitivity design and seeds
   - the eval master seed
3. Generate `EXPERIMENT_PLAN.md` from it.
4. Commit both with the message `prereg: plan v1`.
5. Record the plan hash.

**`marginbench evaluate` refuses to run if any of these hold:**

- the working tree is dirty
- the plan hash does not match the committed file
- the estimator hash differs
- any frozen test fails

Label every evaluation `OPEN_PREREGISTERED`. Git history is the proof of ordering. Never claim secrecy.

**Exclusions:** a replication may be excluded only for a prespecified technical-validity failure, with an audit record. Report all runs, including invalid ones.

---

## 13. Experiments

Every experiment is a config overlay on `default.yaml`. Each ablation changes only its named mechanism.

| ID | Purpose | Overlay | Policies | Replications |
|---|---|---|---|---|
| E0 | Instrumentation sanity | default | P0 | dev, 5 |
| E1 | Aligned world | contractors.identical_quality; callbacks.off; loss.off; retention_null; verify.perfect | P0–P5 | 60 |
| E2 | Static objective mismatch | report.no_suppression; contractors.unlimited_capacity | P0–P5 | 60 |
| **PRIMARY** | Default world | default | P0–P5 | n_eval (≥ 200) |
| E3 | Measurement manipulation | default vs report.no_suppression, paired | P0, P2, P4 | 60 each |
| E4 | Endogenous workload | default vs callbacks.consume_capacity=false vs unlimited_capacity | P0, P2, P4 | 60 each |
| E5 | Observation quality | severity_accuracy ∈ {0.6, 0.8, 0.95, 1.0} | P0, P2, P4 | 40 each |
| E6 | Contract economics and horizon | retention_null; β ×2; negligence share ∈ {0, 0.25, 0.5}; M ∈ {90, 180, 275} | P0, P2, P4 | 40 each |
| E7 | Tail stress | severe hazard ×10, loss log-sd 1.5 | P0, P2, P4, P5 | 100 |
| E8 | Misspecification | M trained on default; eval under the E5/E6 extreme cells and speed-quality corr +0.6 | P0, P2, P4 | 40 each |
| E9 | Evaluation-method comparison | see below | candidates | see below |
| E-DEPLOY | Deployment variant | default, policy continues in maturation | P0, P2, P4 | 60 |

### E1 note

Treat E1 as a sanity check, not an assertion. Report whether P2 vs P0 is ALIGNMENT_SUPPORTED or EQUIVALENCE_SUPPORTED. A REVERSAL_SUPPORTED result in E1 is flagged in the report as a model-validity warning, and the run is still not treated as a code failure.

### E9 design

**Candidates:**

- P1 through P5
- 15 perturbed variants with H_plan ∈ {0, 15, 30}, K = 32, and close-threshold and verification-propensity tweaks, generated by a seeded rule in the plan

**Ground truth:** for each candidate c, the classification of ΔJ(c, P0) from 100 `eval` replications over the full horizon.

**Gates,** each computed on a 30-day pilot with 20 `pilot` replications. Each gate approves c if:

- **(a) Proxy gate:** ΔG CI lower bound > 0.
- **(b) Verified gate:** the verified-resolution-rate difference CI lower bound > 0.
- **(c) Value gate:** ΔJ over pilot plus 60 days maturation, CI lower bound > 0.
- **(d) Risk gate:** (c), plus no increase in severe-loss estimate or SLA breach rate beyond 10% relative.

**Report:** a confusion matrix per gate against the truth, plus false-approval and false-rejection rates with Wilson intervals.

### Required ablations

Run each against default with P0, P2 and P4 at 40 replications:

- callbacks.off
- contractors.unlimited_capacity
- report.no_suppression
- verify.perfect
- retention_null
- obs.perfect
- loss.off
- discount 0
- contractors.identical_quality
- contractors.identical_price
- perfect-estimator (diagnostic, labeled)

---

## 14. Statistics

### 14.1 Replication unit

A replication is one independently seeded portfolio trajectory. Requests within a replication are never treated as independent.

### 14.2 Paired estimates

```
D_i = J_i(a) − J_i(b)
```

Report the mean, sample SD, SE and a two-sided 95% Student-t interval. Do the same for G.

For tail metrics, also report a percentile bootstrap (10,000 resamples, seeded) and quantiles. Label bootstrap results as unreliable when fewer than 20 replications contain a tail event.

### 14.3 Materiality m

```
m = max(0.01 × |mean J(P0)|, $1,000)   on the calib partition (20 reps)
```

Freeze m in the plan.

Sensitivity points use the same rule with that point's own P0 mean, computed from that point's first 10 replications, which are then excluded from inference.

### 14.4 Equivalence

TOST at α = 0.05 with bounds ±m.

### 14.5 Power

From the calib P2-vs-P0 paired SD s, size the sample for 80% power to classify a true effect of magnitude 2m (REVERSAL or ALIGNMENT needs the CI to exclude 0 and the point estimate to pass ±m):

```
n_req = ceil(((t_{0.975} + z_{0.80}) · s / m)²)   (use t_{0.975} ≈ 1.97, z_{0.80} = 0.8416)
n_eval = min(max(200, n_req), 2000)
```

Record in the plan the achieved power for true effects of m and 2m. At |ΔJ| = m exactly, power is about 50% by construction, and the plan must say so. If n_req > 2000, set n_eval = 2000 and note that the primary result may be INCONCLUSIVE.

No adaptive extension.

### 14.6 Classification

Every contrast has a declared type in the plan.

**Proxy-reversal contrasts** are those where a is a proxy-optimized policy and b is P0: (P2, P0) and (P1, P0). Classify into exactly one class, checked in this order:

1. **INVALID:** a validation or reconciliation failure.
2. **UNVERIFIED:** required reproducibility or validation evidence is missing.
3. **PROXY_NOT_IMPROVED:** the ΔG CI lower bound is ≤ 0. ΔJ is still reported.
4. **REVERSAL_SUPPORTED:** the ΔJ CI upper bound is < 0 and the ΔJ point estimate is ≤ −m. Additionally flag STRONG if the CI upper bound is < −m.
5. **ALIGNMENT_SUPPORTED:** the ΔJ CI lower bound is > 0 and the point estimate is ≥ m.
6. **EQUIVALENCE_SUPPORTED:** TOST passes.
7. **INCONCLUSIVE:** anything else.

**Value contrasts** are all other contrasts, such as (P4, P2), (P3, P1), (P5, P4) and (P4, P0). They have no ΔG precondition. Apply steps 1 and 2, then classify ΔJ as:

- VALUE_HIGHER_SUPPORTED (same rule as ALIGNMENT)
- VALUE_LOWER_SUPPORTED (same rule as REVERSAL)
- EQUIVALENCE_SUPPORTED
- INCONCLUSIVE

ΔG is always reported.

For every contrast, the p-value is the two-sided paired t-test of ΔJ = 0. Confidence intervals use the level matching the adjusted α from Section 14.7.

**Run status** is a separate field: `VALID`, `INVALID`, `UNVERIFIED`, `RESOURCE_LIMIT`. A scientific outcome never sets the exit code. Only an invalid or unverified run exits nonzero.

### 14.7 Multiplicity

- **Primary:** (P2, P0) in PRIMARY, unadjusted at α = 0.05, 95% CI.
- **Confirmatory secondary family,** all in PRIMARY. Holm-adjust at family α = 0.05 on the paired t-test p-values. Contrast i, ranked k-th smallest among the 5, gets adjusted α_i = 0.05 / (5 − k + 1) and is classified with a (1 − α_i) two-sided t-interval. Stop the Holm sequence at the first non-rejection; that contrast and all later ones use their Holm α but cannot be classified VALUE_HIGHER, VALUE_LOWER, ALIGNMENT or REVERSAL. Report them as INCONCLUSIVE unless TOST at their α supports EQUIVALENCE. The contrasts are:
  - (P4, P2)
  - (P1, P0)
  - (P3, P1)
  - (P5, P4)
  - (P4, P0)
- Everything else is labeled EXPLORATORY.

---

## 15. Sensitivity design

Latin hypercube with 48 points (seeded `sens`) over the dimensions below. Each point runs 40 replications of P0, P2 and P4, with M retrained per point (Section 10.3).

| Dimension | Range |
|---|---|
| Contractor success dispersion: multiply spread of logit(s_c) around the mean | 0 to 2 |
| Speed-quality correlation: reassign speeds to impose rank correlation | −0.6 to +0.6 |
| Price-quality correlation: same | −0.6 to +0.6 |
| m_sev scale for callback reporting | 0.5 to 1.2 (capped at probability 1) |
| Report delay scale | 2 to 10 days |
| m_close | 0.6 to 1.0 |
| Verification cost | $5 to $60 |
| Verification sensitivity | 0.6 to 1.0 |
| β multiplier on retention | 0 to 3 |
| Capacity multiplier | 0.5 to 2 |
| Arrival-rate multiplier | 0.5 to 2 |
| Severe hazard multiplier | 0 to 5 |
| H_plan | 15 to 90 |
| Discount rate | 0 to 20% |

**Output per point:**

- ΔG and ΔJ with CIs
- the classification for (P2, P0) and (P4, P2)
- `sensitivity.csv`

**Charts:** two 2-D panels on the two dimensions with the largest |Spearman ρ| against ΔJ(P2, P0). Report the share of points in each class, labeled as the share of *tested design points*, never as a real-world probability.

---

## 16. Metrics catalogue

Every metric is defined in `evaluation/metric_defs.yaml` with:

- name, numerator, denominator, cohort, window
- inclusion rules, missingness rule, units, direction
- source class (observed / estimated / latent)
- whether policies can see it
- definition version

Undefined values serialize as `null` with a reason. They are never 0.

**Operational:**

- closure rate within target
- verified resolution rate
- true resolution rate (latent)
- mean and median times
- callback rate per completed attempt
- reopen rate
- escalation rate
- verification rate
- backlog and backlog age
- contractor utilization
- unreported-failure count (latent)

**Economic:**

- fees
- each expense category
- operator contribution, nominal and discounted
- owner costs by category
- realized losses by principal
- contracts lost
- boundary obligations (Section 6.4)

**Model:** Brier, calibration error, censoring fraction, per-category error, out-of-distribution performance (E8).

**Risk:**

- P(J below the 5th percentile of P0's J)
- realized severe-loss frequency vs estimated
- loss quantiles
- CVaR at 5% where at least 20 tail replications exist
- P5 constraint-violation rate and fallback rate

---

## 17. Repository, dependencies, CLI, artifacts

### 17.1 Layout

```
marginbench/
  pyproject.toml   requirements.lock (or uv.lock)   README.md   SPEC.md
  ASSUMPTIONS.md   LIMITATIONS.md   DECISIONS.md   EXPERIMENT_PLAN.md
  CLAIMS.md   RESULTS_SUMMARY.md   LICENSE (MIT)   .gitignore
  configs/  default.yaml aligned.yaml static_mismatch.yaml reporting.yaml
            congestion.yaml retention_null.yaml stress.yaml ablations/*.yaml plan.yaml
  models/   estimator_v1.json
  src/marginbench/
    cli.py config.py schemas.py hashing.py
    environment/  engine.py events.py state.py observations.py actions.py arrivals.py
                  contractors.py repairs.py callbacks.py verification.py sla.py
                  losses.py retention.py randomness.py
    economics/    ledger.py contracts.py valuation.py reconciliation.py
    policies/     base.py internal_model.py baseline.py proxy.py economic.py
                  constrained.py oracle.py runner.py
    estimation/   history.py training.py estimator.py audit.py
    experiments/  runner.py pairing.py partitions.py ablations.py sensitivity.py
                  e9_gates.py prereg.py
    evaluation/   metric_defs.yaml metrics.py statistics.py classification.py
                  validation.py provenance.py
    reporting/    charts.py html.py claims.py summary.py
  tests/  unit/ property/ integration/ boundary/ reproducibility/ statistical/
          fixtures/ FROZEN.txt
  scripts/ smoke.sh evaluate.sh reproduce.sh check_frozen_tests.py
  results/ .gitkeep
```

### 17.2 Dependencies

Pin all of these:

- numpy
- scipy
- pandas
- pydantic v2
- scikit-learn
- pyyaml
- matplotlib (Agg backend)
- jinja2
- typer
- pytest
- hypothesis

**Lockfile:** use `uv lock` if uv is available, otherwise `pip-compile` to produce `requirements.lock`. Record the lock hash in manifests.

**Git:** run `git init` if no repository exists.

**Parallelism:** parallelize replications with `multiprocessing` only when results are byte-identical to serial execution. A test enforces this on 4 replications.

### 17.3 CLI

All commands live under `marginbench`:

- `validate --config`
- `smoke --config`
- `train --config`
- `prereg --config`
- `evaluate --plan configs/plan.yaml --output results/primary`
- `experiment --id E3 --output`
- `ablate --output`
- `sensitivity --output`
- `report --results --output`
- `reproduce --manifest`
- `audit --results`

**Exit codes:** 0 for a valid run whatever the scientific result, 2 for INVALID, 3 for UNVERIFIED, 4 for RESOURCE_LIMIT.

### 17.4 Artifacts per run directory

- `run_manifest.json`
- `config.json`
- `plan_hash.txt`
- `policy_manifest.json`
- `estimator_manifest.json`
- `metrics.json`
- `paired_results.csv` (one row per replication × contrast)
- `boundary.json`
- `policy_diagnostics.json`
- `validation.json`
- `claim_audit.json`
- `charts/`
- `report.html`

**Full traces** (`events.jsonl`, `actions.jsonl`, `ledger.jsonl`) are written for the first 3 replications per arm. Every replication records the SHA-256 of its canonical event stream and ledger.

**Manifest contents:**

- run_id
- UTC time (excluded from hashes)
- git commit and dirty flag
- lock hash
- Python version and platform
- sim, policy and metric-definition versions
- config hash, estimator hash, plan hash
- partition
- seed manifest
- random-stream schema version
- run status
- reproducibility status

**Canonical JSON:** sorted keys, no whitespace, floats via `repr` (shortest round-trip), timestamps as integer ticks.

**Checkpointing:** write each completed replication atomically (temp file then rename). Support resume. Refuse to merge replications whose manifests differ in any hashed field.

**Resource limits** (configurable): max events per replication (2,000,000), max wall time per experiment. Exceeding a limit gives RESOURCE_LIMIT. Never truncate silently.

**Runtime budget:** time the smoke run and extrapolate. If the projected time for PRIMARY exceeds 3 hours, reduce K for all planning policies equally, down to a floor of 16, and record this in `DECISIONS.md` before preregistering. Never reduce n_eval to save time. Cut Tier 3 sensitivity points first, keeping at least 24 points.

---

## 18. Tests

### 18.1 Frozen tests

**The frozen set** is every test in unit/, property/, boundary/, reproducibility/ and statistical/ written during Phases A and B (Section 20).

**Freezing procedure:**

1. List the files with their SHA-256 hashes in `tests/FROZEN.txt`.
2. Commit with the message `tests: freeze v1`.
3. `scripts/check_frozen_tests.py` fails if any listed file changed. It runs in `pytest` via a session fixture, and in `evaluate`.

New test files may be added later. Frozen files may never be edited. If a frozen test is wrong, document it in `DECISIONS.md` and add a corrected new test. The original stays and is marked xfail **only** through an entry in `tests/XFAIL_REASONS.txt`, and the report lists it.

### 18.2 Unit tests

- config validation
- each lifecycle transition, legal and illegal
- event ordering (tick, priority, event_id)
- capacity scheduling
- repair probability formula
- report, verification, callback and SLA logic
- loss payer rule
- retention hazard
- fee accrual summing exactly over 365 days
- ledger reconciliation
- discounting
- every metric denominator, including N = 0

### 18.3 Property tests (Hypothesis)

- no impossible transitions
- no negative capacity
- no duplicate fee or expense entries
- all probabilities in [0, 1]
- monotone ticks
- no future events in observations
- every ledger entry references an existing event and request
- correct behavior with zero arrivals, all-success and all-failure fixtures

### 18.4 Boundary tests

- adding a new LATENT field leaves serialized observations unchanged
- unknown fields are rejected
- EVALUATOR_ONLY records never appear in feedback
- mutating a received observation does not change engine state
- `policies/` does not import `environment/` (AST check)
- feasible policies have no reference path to the engine, by an introspection check on the objects passed in
- master_seed, replication index, partition and environment stream keys are not recoverable from PublicConfig, observations, feedback or Monte Carlo seeds
- legal-action sets never depend on LATENT or EVALUATOR_ONLY fields. Test this by holding observations fixed, varying latent state, and asserting identical legal actions.

### 18.5 Reproducibility and statistics tests

**Reproducibility:**

- identical runs give identical hashes
- changing only the policy leaves the arrival list identical
- reordering processing of unrelated entities leaves keyed draws unchanged
- different master seeds diverge
- replay reconstructs the ledger
- parallel equals serial

**Analytic fixtures** (tiny worlds solvable exactly):

- paired mean, SE and t-interval against hand-computed values
- TOST behavior
- every classification branch for both contrast types
- the Holm stopping rule
- Holm adjustment
- identical policies give D_i = 0 exactly
- a fully aligned toy world where the proxy-optimal policy is value-optimal, with exact computed values (true regret allowed here)
- a toy misaligned world where the exact values show a reversal

Never test that one policy beats another on an arbitrary stochastic seed.

### 18.6 Outcome-path tests

The pipeline produces each of these without exceptions, using synthetic `paired_results` fixtures:

- REVERSAL_SUPPORTED
- ALIGNMENT_SUPPORTED
- VALUE_HIGHER_SUPPORTED
- VALUE_LOWER_SUPPORTED
- EQUIVALENCE_SUPPORTED
- INCONCLUSIVE
- PROXY_NOT_IMPROVED
- INVALID
- UNVERIFIED

---

## 19. Reports and documents

### 19.1 HTML report

Self-contained: inline CSS, PNGs base64-embedded, no network. It must be readable at phone width.

Every chart caption carries its run_id and config hash.

**Required charts:**

1. Proxy vs operator contribution per policy (two panels, separate units).
2. Paired ΔJ with 95% CI for every contrast, with the materiality band shaded.
3. Closure rate vs verified vs true resolution.
4. Callback and backlog trajectories over time.
5. Cumulative discounted contribution over time with the decision/maturation boundary marked.
6. Sensitivity panels.
7. Estimator calibration plots.
8. A decision-to-cash provenance trace for one request: actions, events and ledger entries, labeled "modeled dependency".

Never put dollars and percentages on one axis.

### 19.2 Documents

- **`CLAIMS.md`**, generated from `claim_audit.json`, with sections: supported synthetic findings / supported model-family findings / unsupported or inconclusive / required external validation. Every claim lists its metric, contrast, scenario, cohort, horizon, estimate, CI, units, run_id and artifact path.
- **`RESULTS_SUMMARY.md`:** question, design, primary contrast and its classification with interval in the first paragraph (say INCONCLUSIVE there if it is), secondary results, E1 sanity outcome, E9 gate comparison, sensitivity summary, limitations, reproduce command.
- **`ASSUMPTIONS.md`:** one row per mechanism and parameter. Columns: description, config key, synthetic or calibrated (all synthetic in v1), expected influence, covering ablation or sensitivity dimension, limitation.
- **`LIMITATIONS.md`:**
  - synthetic validity
  - no tenant move-outs
  - no contract replacement
  - first-order retention term in planning
  - no congestion shadow price
  - censoring and selection in estimator labels
  - tail estimation
  - in-process isolation only
  - open preregistration only
  - no external calibration
- **`README.md`:** what it is, the question, why proxies diverge in principle, environment overview, policy table, install and run, reproduce, what results can and cannot support, how to read null and opposite results.

---

## 20. Build phases and gates

Each phase ends with its tests passing and a commit. Do not start a phase while the previous phase's tests fail.

- **Phase A, foundation:** package skeleton; config schemas; immutable schemas; hashing; keyed randomness; canonical JSON; unit and property tests for these.
- **Phase B, environment and economics:**
  - entities; arrivals; workflow; contractors and scheduling; repair, report, verification, callbacks, SLA, losses, retention; fees and ledger; reconciliation; replay
  - P0
  - boundary tests and the analytic fixtures
  - **freeze tests** (Section 18.1)
- **Phase C, estimation:** history generation with propensities; estimator training and freeze; estimator audit.
- **Phase D, policies:** internal model; P1 and P3, then P2, P4 and P5; matched-compute diagnostics; P6 last (Tier 3).
- **Phase E, experiments and statistics:** pairing; runner with checkpoints; statistics; classification; Holm; E0, E1, E2 on dev to validate the pipeline; ablations; E9; sensitivity.
- **Phase F, preregistration and locked runs:**
  - calib runs, materiality, power, `plan.yaml`
  - commit `prereg: plan v1`
  - PRIMARY, then E3 to E8, E9, ablations, sensitivity, all from a clean tree
- **Phase G, reporting and audit:** charts; HTML; generated documents; `marginbench audit` on every results directory; `reproduce` on PRIMARY replication 0 for every arm.

### Acceptance gates

All must pass for status COMPLETE.

1. Executability.
2. Every frozen test passes and the hash check passes.
3. Matched information verified by the boundary tests.
4. Ledger reconciles in every run.
5. Every mechanism ablatable, with no policy-specific penalties anywhere in the environment.
6. Reproduce matches the hashes.
7. Statistics fixtures pass.
8. Plan committed before PRIMARY, with evaluate's guard enforced.
9. Every outcome path is producible.
10. Every figure and claim traces to a run.
11. Documents complete.
12. Nothing claimed that was not executed.

---

## 21. Required final response

Return in this order:

1. **Status:** COMPLETE or PARTIAL, plus the last completed tier and the final commit hash.
2. **Verification:**
   - the test command and its pass, fail and xfail counts
   - frozen-hash check
   - smoke result
   - audit results
   - reproduce result
3. **Primary result:** ΔG and ΔJ for (P2, P0) with CIs, n, m and classification.
4. **Secondary results:** the Holm-adjusted results.
5. **E1 outcome,** the E9 gate table, and the sensitivity class shares.
6. **Paths:** report.html, charts, manifests, and the reproduce command.
7. **Deviations:** every deviation from this document and every entry in `DECISIONS.md` and `XFAIL_REASONS.txt`.
8. **Incomplete items:** any requirement left incomplete, listed without omissions.

The instrument succeeds when it produces an auditable map from declared assumptions and decisions to outcomes, with honest uncertainty. A striking chart is not a success criterion.

---

## Appendix: resolutions of defects in earlier drafts

These are binding. They exist so you do not re-introduce the defects.

1. **The primary contrast was P2 vs P4 with inconsistent sign conventions.** It is now P2 vs P0, using the reversal definition in 2.3. P4 vs P2 is a confirmatory secondary.
2. **Result classes mixed run validity with scientific outcome.** They are now separate fields, with an explicit proxy-improvement precondition (PROXY_NOT_IMPROVED).
3. **Materiality was computable from evaluation data.** It is now frozen from calib before evaluation.
4. **Most mechanisms had no defaults, so the implementer would have invented them.** Section 5 now specifies every mechanism and number, labeled synthetic.
5. **The fixture had no fast-unreliable contractor, so the dispatch channel could not express the tension.** D now fills that role, declared openly, with speed-quality correlation swept to +0.6 and an aligned world E1.
6. **Warm-up and post-decision behavior were undefined, which confounded maturation.** P0 now runs warm-up and continuation for every arm, so arms start from identical state and differ only by decision-window choices. The deployment variant is secondary.
7. **The proxy was "to be defined".** It is now fixed as `proxy_v1` before any run.
8. **Repair randomness keyed by contractor would break coupling.** The success uniform is now keyed by (request, attempt), giving monotone coupling.
9. **"Planning" via rollouts of the true simulator would leak information and cost too much.** Planning now uses a request-level Monte Carlo on a separate internal model that is never allowed to import `environment/`, with matched K, H and seeds.
10. **Subprocess isolation and "external runners" were promised but unverifiable in one session.** v1 is in-process with a stated software contract and open preregistration enforced by git and hashes.
11. **The spec required both a one-shot build and an untouchable test set.** Frozen tests are now enforced by hash after Phase B: new tests are allowed, edits are forbidden. This keeps the implementer from grading itself.
12. **The plan was a Markdown file passed to the CLI.** The machine plan is now `plan.yaml`, and the Markdown is generated from it.
13. **Full traces for every replication would be impractical.** Traces are written for 3 replications per arm, with hashes for all.
14. **Tenant churn and contract replacement were half-specified.** Both are excluded in v1 and listed as limitations.
15. **The retention effect of planning was unspecified.** It is now a declared first-order formula shared by all economic policies.
16. **Several channels leaked latent state to policies.** P0's prior, attempt limits, SLA tiering, invoices and Monte Carlo seeds all now use only observable or public information, and legal-action sets are tested to be independent of latent state.
17. **Follow-on decisions inside rollouts implied nested Monte Carlo.** They now use P0's rule with M's estimates.
18. **Holm had no p-values, and the ΔG precondition blocked value contrasts.** p-values are now paired t-tests, Holm sets the CI levels, and value contrasts skip the ΔG precondition.
19. **The absolute P5 risk thresholds were infeasible for most urgent requests.** They are now relative to the best legal action, and the fallback is always legal.
