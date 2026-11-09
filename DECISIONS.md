# DECISIONS

Where SPEC.md was silent or self-contradictory, the smallest defensible choice is recorded here with a one-line reason. Numbered entries are referenced from code comments.

## Build and packaging

- **D-01** Python 3.12 (uv-managed); dependencies pinned in `pyproject.toml`, locked in `uv.lock`, exported to `requirements.lock`. Reason: SPEC 17.2 prefers uv when available.
- **D-02** The repository root is the `marginbench/` project directory of SPEC 17.1. Reason: the repo is the project.
- **D-03** `tests/helpers.py` and `tests/conftest.py` are hashed in `tests/FROZEN.txt` along with the five frozen test directories. Reason: frozen tests import them, so editing them would change frozen behaviour.

## Environment

- **D-04** Same-tick event priority: DAY_START < WORK_START < SLA_CHECK < WORK_COMPLETE < VERIFY_RESULT < INFO_ARRIVES < DEFER_ELAPSES < CALLBACK < ARRIVAL; events emitted while handling another take its priority. Reason: SPEC 7.3 orders by (tick, priority, event_id) without listing priorities; work starting exactly at the SLA deadline must count as on time.
- **D-05** Contract termination hands the property over: on the effective date every request at the property leaves the operator's system (HANDOVER event; pending events for it are dropped), later arrivals there are OPPORTUNITY_UNSERVED, and no further hazards or callbacks are processed for it. A cohort request handed over before its first closure counts as not closed. Reason: SPEC 4.5 says lost contracts are not replaced and the portfolio only shrinks, but does not say what happens to open work.
- **D-06** A callback does not increment attempt_index. Reason: SPEC 4.4 and 7.1 say so; 5.8's "attempt count + 1" conflicts, and the transition table is declared the single source of truth.
- **D-07** Arrival streams are generated per (unit, category) for 400 days and truncated to the run's horizon. Reason: keeps every arrival prefix identical across horizons (M = 90/180/275) and equals generating days 0..W+D+M-1.
- **D-08** Opportunity ids are `{unit}-{cat}-{n}` (n-th arrival of that stream); true severity, reported severity and the request_info resample are drawn from generators keyed by opportunity id at world build. Reason: SPEC 11 couples latent request attributes by opportunity id.
- **D-09** Severe-loss occurrence for (request, day) uses element `day` of the request's keyed loss stream; the hazard for day d−1 is checked at the start of day d (event tick d·1440). Reason: a pure function of (request, day) as SPEC 11 requires, and one generator per (mechanism, entity) as SPEC 11 describes.
- **D-10** Termination for (contract, day) uses element `day` of the contract's keyed stream. Reason: same as D-09.
- **D-11** `defer` is legal when no SLA exposure is pending (first work already started) and illegal after a breach. Reason: SPEC 7.2 defines slack only while an SLA is pending.
- **D-12** The runner hands each decision's Monte Carlo seed to the policy as `Observation.mc_seed`; `decision_index` counts decisions on that request. Reason: the Policy protocol (SPEC 9) has no seed parameter; a per-request index lets matched policies share samples at the same decision.
- **D-13** `Policy.reset` receives `initial_observation=None`. Reason: no request exists when a run starts.
- **D-14** P0's p-hat: the public prior 0.80 during history generation (before M exists), M's p-hat afterwards. Reason: SPEC 9.2.
- **D-15** SLA tier and deadline are fixed when the request first reaches DISPATCH_READY; a check is scheduled at max(deadline, now); a breach occurs if no work has started by the deadline. Reason: SPEC 5.9.
- **D-16** Contractor invoices are booked at work completion, priced at dispatch on the reported severity; OC90 (owner spend) counts invoices only. Reason: SPEC 5.12 prices at dispatch; an invoice follows the work.
- **D-17** The repair formula's attempt j is the number of prior jobs (attempt_index before it increments on entering QUEUED). Reason: SPEC 5.5 says j is 0-indexed.
- **D-18** The verification outcome is drawn at the result event; physical state cannot change between the action and the result. Reason: equivalent either way; keyed by (request, verification_index).
- **D-19** A benign repeat is drawn once per request, at its first closure while physically resolved. Reason: SPEC 11 keys the benign draw by request only.
- **D-20** Escalation starts at dispatch + ceil(360/speed) minutes. Under `callbacks.consume_capacity=false`, every later dispatch of a callback-reopened request uses the same overtime timing, without capacity and without the $35 surcharge. Reason: SPEC 5.4.
- **D-41** Queue length is the number of scheduled jobs not yet started; jobs of handed-over requests stay booked. Reason: later jobs never bump scheduled jobs (SPEC 5.4).
- **D-42** Property risk is lognormal with log-mean −σ²/2 so its mean is 1. Reason: SPEC 4.1 states mean 1.
- **D-43** A tenant's known complaint count increments on each arrival and each callback. Reason: both are tenant contacts.
- **D-40** After the freeze, `AttemptView` gained `closed_tick` and `callback_tick` (OBSERVABLE_AFTER_EVENT, allowlisted, defaulted so frozen tests that build views positionally are unchanged). Reason: the internal model needs to know which attempt a callback followed.
- **D-46** Fee day index is the simulation day; every contract starts on day 0. Reason: SPEC 5.12 accrues from contract start.
- **D-48** Boundary "estimated future fees at risk" is the annual fee of every contract in notice or terminated, plus fees still to accrue in notice after the horizon; both are labeled estimates and excluded from J. Reason: SPEC 6.4 asks for the estimate without a formula.

## Estimator M

- **D-21** The success model is first fit as SPEC 10.2 specifies (labels only from verification or callback, unverified attempts without a callback excluded). Those selection-biased labels make the report/verification rates unidentifiable: an EM over them converged to sensitivity 0.44 against a true 0.90. The final M is a latent-class EM over all matured attempts: physical success is the latent class, observables are the contractor report, the verification result and whether a callback followed the close; rates get Beta(1,1) posterior-mean M-steps; the logistic success model is refit on soft labels each outer iteration (40 outer, 100 inner, fixed). It is run from two fixed starts (flat 0.75, and the selection-labeled model) and the start with the higher observed-data log-likelihood is kept. No truth enters the choice. Reason: the smallest change that makes the rates identifiable from observable data; the selection-labeled model is kept in the estimator file for audit.
- **D-22** Severe-loss hazard: Poisson rate per expected unresolved request-day by reported severity, Gamma(1, 1000) shrinkage. Exposure is arrival-to-first-completion days plus, for later intervals, the smoothed P(unresolved): 1 until an observed callback, otherwise the posterior given no callback by the interval's end. Reason: losses also strike closed latent failures; open-days-only exposure overstated the rate fivefold, filtering-only exposure understated it.
- **D-23** The callback model is a logistic regression of "callback within 60 days" on (reported severity, closed-unverified) over matured closures, each weighted by its EM posterior probability of failure. Benign callbacks are a separate EM rate. Reason: SPEC 10.2's "failures detected by verification" can never be closed (VERIFIED_FAIL only allows redispatch), so failures are identified probabilistically.
- **D-24** M also holds an empirical request_info transition matrix P(reported after | reported before) with Dirichlet(1) shrinkage. Reason: the internal model must simulate request_info, and only observable data may inform it.
- **D-32** Sensitivity points and E8 cells retrain M on 20 training plus 5 calibration portfolios generated under the point's parameters. Reason: SPEC 10.3 retrains on 20 training portfolios; the 5 calibration portfolios choose regularization as in the main fit.
- **D-38** The perfect-estimator ablation uses population-true parameters from the config (fixture contractor qualities, true report/verification rates, mean tenant propensity, true hazards and betas). It does not know per-replication perturbations or latent state. Labeled a diagnostic.

## Policies and internal model

- **D-25** Internal model simplifications, identical for every policy: job duration fixed at 120 minutes; the first dispatch uses the exact public earliest start; follow-on dispatches use M's empirical lead days; severe loss is drawn once per unresolved segment with probability 1 − (1 − ĥ)^days; loss size is M's mean; the operator share uses the public negligence share; the myopic rollout stops at the request's next decision point with a 365-day safety cap and no retention term (T_rem = 0); the proxy objective's cost term matches proxy OPEX (no severe-loss share); the closure bonus applies only if the request has no first closure yet.
- **D-26** Retention-term weights: callback w = 1/units (CB90), breach w = 1 (BR90), severe loss w = 1 (SL365), invoice w = invoice/units/100 (OC90); ĥ_now is M's GLM hazard at the property's current trailing features; F_c is the contract's daily fee. Reason: SPEC 9.1's first-order formula needs w_x per feature.
- **D-27** A decision with exactly one legal action is taken without Monte Carlo, for every policy. Reason: there is nothing to value; compute stays matched.
- **D-28** P5's P(SLA breach) is the probability that the action leads to a new breach within the horizon; its close constraint uses the history belief P(unresolved). Reason: SPEC 9.2.
- **D-23b** The internal model's belief P(unresolved | history) starts at 1 and is updated attempt by attempt with M's success, report and verification rates, and by Bayes on each callback (true-callback probability vs M's benign rate).
- **D-45** The history behavior policy draws its randomness from the per-decision seed. Reason: no global RNG.

## Statistics and classification

- **D-29** Closure-rate tiers use the SLA tier (reported severity at the first dispatch decision). Reason: SPEC 8 says reported severity; this fixes which report.
- **D-30** Callback rate = callbacks on cohort requests by the cutoff ÷ completed cohort attempts by the cutoff; verification rate = verify actions ÷ close actions on cohort requests by the cutoff.
- **D-35** A Holm-stopped contrast can still be INVALID, UNVERIFIED or PROXY_NOT_IMPROVED; it cannot be directional. Reason: SPEC 14.7 restricts only the directional classes.
- **D-36** STRONG is flagged for REVERSAL_SUPPORTED and VALUE_LOWER_SUPPORTED only. Reason: SPEC 14.6 defines STRONG for reversal; VALUE_LOWER uses "the same rule as REVERSAL".
- **D-37** Each experiment re-runs its first replication and compares canonical hashes before classifying; a mismatch makes the run UNVERIFIED. Reason: SPEC 14.6 step 2 needs reproducibility evidence.
- **D-31** Sensitivity points run 10 + 40 replications: the first 10 set the point's materiality and are excluded from inference. Reason: SPEC 14.3 and 15 together.
- **D-39** Locked secondary experiments (E1-E6, E8, E-DEPLOY, ablations, P6 diagnostic) use `eval` replications 0..n−1, the same seeds as PRIMARY's first n; E7 uses `stress`; sensitivity uses `sens`; E9's pilot uses `pilot`. Reason: common random numbers across experiments; SPEC 12 names the partitions without assigning every experiment.

## Experiments

- **D-33** E8 compares, in each extreme cell, M trained on the default world against M retrained on the cell. Reason: SPEC 13's E8 keeps default M; E5/E6 already use default M, so the retrained comparator is what isolates misspecification.
- **D-34** E9: 15 variants are sampled without replacement (seeded, seed in the plan) from a 54-cell grid of objective × H_plan ∈ {0,15,30} × close threshold {none, 0.1, 0.3} × verification bonus {none, low, high}. The pilot is D = 30, M = 60 on the `pilot` partition. The risk gate compares mean realized severe-loss counts and SLA breach counts per replication. Truth positive = ΔJ(c, P0) classified VALUE_HIGHER_SUPPORTED on 100 eval replications.
- **D-47** P6 runs as a separate 60-replication diagnostic (P0, P4, P6) and is never in PRIMARY.

## Deviations

- **DEV-1** During the Phase E pipeline dry-run, E9 and sensitivity code paths ran on 4 `eval` and 3 `pilot` replications (E9) and on 3 `sens` points with 5 replications each, instead of `dev` only (SPEC 12). The outputs were deleted after a status check; no number from them informed any design choice, threshold or plan value. The locked runs use the same partitions; this is disclosed here because it breaks the letter of "use only dev for development".
