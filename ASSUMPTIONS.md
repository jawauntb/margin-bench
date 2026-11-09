# ASSUMPTIONS

Every value is a **synthetic engineering fixture**, not an industry estimate, and must never be cited as market data. All values live in `configs/default.yaml`; none are calibrated (v1 has no external calibration).

| Mechanism / parameter | Description | Config key | Synthetic or calibrated | Expected influence | Covering ablation or sensitivity dimension | Limitation |
|---|---|---|---|---|---|---|
| Portfolio | 20 properties × 10 units, one tenant per unit | `portfolio.*` | synthetic | scale of J and of noise | arrival-rate multiplier | no tenant move-outs, no contract replacement |
| Property risk | lognormal, mean 1, log-sd 0.3, LATENT | `portfolio.property_risk_log_sd` | synthetic | heterogeneity of arrival rates | `arrivals.heterogeneous` | none |
| Property condition | Beta(5,2) LATENT; grade = q + N(0, 0.1) PUBLIC | `portfolio.condition_*` | synthetic | repair success | `obs.perfect` | single condition factor |
| Tenant reporting propensity | Beta(8,2) LATENT | `portfolio.tenant_report_beta_*` | synthetic | callback rate | m_sev scale | fixed per tenant |
| Arrivals | 0.012/unit-day × category share × risk × hvac seasonality | `arrivals.*` | synthetic | workload | arrival-rate multiplier; `arrivals.seasonal` | Poisson, policy-independent |
| True severity | category-specific distribution | `severity.probs` | synthetic | SLA, loss exposure, invoice | none | three classes |
| Reported severity | equals true w.p. 0.80, else adjacent | `obs.severity_accuracy` | synthetic | triage errors | E5; `obs.perfect` | adjacent-only errors |
| request_info | 1 day, $6, accuracy 0.95 | `obs.info_*`, `costs.info` | synthetic | value of information | E5 | single resample |
| Contractors | A cheap/unreliable, B mid, C expensive/reliable, D fast/unreliable | `contractors.fixtures` | synthetic | dispatch trade-off | identical_quality, identical_price; dispersion, speed-quality and price-quality correlations | four contractors |
| Contractor perturbation | logit N(0,0.2), price ×(1+N(0,0.05)), category offsets N(0,0.3) | `contractors.*_sd` | synthetic | estimator error | success dispersion | per replication |
| Fast-unreliable contractor D | declared: speed 1.5 with success 0.70 | `contractors.fixtures` | synthetic | proxy-value tension in dispatch | speed-quality correlation −0.6..+0.6; E1 aligned world | default world contains this tension by construction |
| Lead time | ceil(L_k/speed) days; capacity per day | `contractors.base_lead_days`, `capacity_multiplier` | synthetic | SLA and closure timing | capacity multiplier; unlimited_capacity; E4 | no shadow price for congestion in planning |
| Repair success | logit(s_c) + a_ck + b_sev + 1.0(q − 0.7) − 0.4 j | `repair.*` | synthetic | callbacks, rework | identical_quality | no learning |
| Contractor report | complete w.p. 0.98 on success, 0.80 on failure | `report.*` | synthetic | false completion | verify_perfect (indirect) | none |
| Verification | $18, 1 day, sensitivity 0.90, specificity 0.95 | `verify.*` | synthetic | cost of truth-seeking | verify_perfect; verification cost and sensitivity | none |
| Callbacks | ρ × m_sev × m_close (0.85 unverified), Gamma(2,4 d) delay; benign repeats 3% | `callbacks.*` | synthetic | measurement manipulation, delayed cost | callbacks_off; no_suppression; E3; m_sev scale, delay scale, m_close | unreported failures stay latent |
| Callback capacity | re-dispatch after a callback consumes capacity | `callbacks.consume_capacity` | synthetic | endogenous workload | E4 | none |
| SLA | 24 h / 72 h / 7 d to first start; credits $40 / $15 / $0 | `sla.*` | synthetic | proxy and cash penalty | none directly | tiered by reported severity |
| Severe loss | daily hazard 0.004 urgent / 0.0005 moderate while unresolved; lognormal sizes; operator pays 25% if negligent | `loss.*` | synthetic | tail risk | loss_off; E7; severe hazard multiplier; E6 negligence share | at most one per request |
| Owner retention | daily hazard h0·exp(β·features); 30-day notice | `retention.*` | synthetic | long-horizon fee loss | retention_null; E6 β×2; β multiplier | contracts are not replaced |
| Fees | $120 per unit-month, exact cents | `fees.per_unit_month` | synthetic | revenue scale | none | flat fee |
| Operator costs | dispatch $12, callback $20, escalation $35, info $6 | `costs.*` | synthetic | direct cash | verification cost | none |
| Invoices | base × severity multiplier × price, paid by the owner | `invoice.*` | synthetic | owner spend (retention) | identical_price | owner, not operator |
| Discounting | 10%/year | `time.annual_discount_rate` | synthetic | weight on maturation | discount_0; discount rate 0-20% | none |
| Horizon | W 30, D 90, M 180 | `time.*` | synthetic | how much delayed value counts | E6 M ∈ {90,180,275} | no terminal value |
| Proxy | first-closure rate within 2/5/10 days minus 0.5·(opex/N)/25; reopens do not reduce CR | `proxy.*` | declared dashboard definition | what proxy policies chase | E1, E2 | one definition (proxy_v1) |
| Planning | K 32, H_plan 60 d, rollout rule = P0 with M | `planning.*` | synthetic | policy strength | H_plan 15-90 | first-order retention term |
