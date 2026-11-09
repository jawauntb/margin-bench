# MarginBench experiment plan (v1)

Generated from `configs/plan.yaml` by `marginbench prereg`. The YAML file is the binding plan; this page restates it.

Label: **OPEN_PREREGISTERED**. The evaluation is open and preregistered, not blind. Git history proves the ordering:
this plan is committed as `prereg: plan v1` before any locked evaluation runs.

## Primary contrast

- P2 (proxy-planning) against P0 (operating baseline), in the default world, on the `eval` partition, n = 200 paired replications.
- Estimands: ΔJ (discounted operator contribution, days 30-299) and ΔG (proxy_v1).
- Type: proxy-reversal contrast, unadjusted α = 0.05, two-sided Student-t 95% interval.
- Materiality m = $1,774.97 (max(1% of |mean J(P0)|, $1,000) on 20 calib replications; mean J(P0) = $177,497.29).

## Power

- Calib paired SD of ΔJ(P2, P0): $2,176.62. n_req = 12, n_eval = 200 (floor 200, cap 2000).
- Achieved power (normal approximation, CI must exclude 0 and the estimate must pass m): 0.500 at |ΔJ| = m, 1.000 at |ΔJ| = 2m.
- At |dJ| = m exactly, power is about 50% by construction (the point estimate must pass m).
- No adaptive extension.

## Confirmatory secondary family (Holm, family α = 0.05)

- P4 vs P2
- P1 vs P0
- P3 vs P1
- P5 vs P4
- P4 vs P0

The k-th smallest p-value gets α = 0.05/(5 − k + 1) and a (1 − α) interval; the sequence stops at the first non-rejection, and that contrast and all later ones cannot be classified directional.

## Classification

Order: INVALID, UNVERIFIED, PROXY_NOT_IMPROVED (proxy contrasts only), REVERSAL/VALUE_LOWER, ALIGNMENT/VALUE_HIGHER, EQUIVALENCE, INCONCLUSIVE. TOST with bounds ±m for equivalence. Run status (VALID/INVALID/UNVERIFIED/RESOURCE_LIMIT) is a separate field.

## Experiments

| ID | partition | n | policies | scenarios |
|---|---|---|---|---|
| E0 | dev | 5 | P0 | default |
| E1 | eval | 60 | P0, P1, P2, P3, P4, P5 | aligned |
| E2 | eval | 60 | P0, P1, P2, P3, P4, P5 | static_mismatch |
| PRIMARY | eval | 200 | P0, P1, P2, P3, P4, P5 | default |
| E3 | eval | 60 | P0, P2, P4 | default, no_suppression |
| E4 | eval | 60 | P0, P2, P4 | default, callbacks_no_capacity, unlimited_capacity |
| E5 | eval | 40 | P0, P2, P4 | acc_0.6, acc_0.8, acc_0.95, acc_1.0 |
| E6 | eval | 40 | P0, P2, P4 | default, retention_null, beta_x2, negligence_0, negligence_0.5, M_90, M_275 |
| E7 | stress | 100 | P0, P2, P4, P5 | tail_stress |
| E-DEPLOY | eval | 60 | P0, P2, P4 | deploy |
| P6-DIAG | eval | 60 | P0, P4, P6 | default |
| ABLATIONS | eval | 40 | P0, P2, P4 | default, callbacks_off, unlimited_capacity, no_suppression, verify_perfect, retention_null, obs_perfect, loss_off, discount_0, identical_quality, identical_price, perfect_estimator |
| E8 | eval | 40 | P0, P2, P4 | acc_0.6, acc_1.0, beta_x2, negligence_0.5, M_275, speed_quality_+0.6 × (default M, retrained M) |
| E9 | eval (truth, 100) + pilot (20) | - | P1-P5 + 15 seeded variants | default; 30-day pilot |
| Sensitivity | sens | 10 + 40 per point | P0, P2, P4 | 48 LHS points |

## Frozen inputs

- Estimator `models/estimator_v1.json` sha256 `2147cba34506c0f765bc5bb9dd24128042770855b8e7c1b503ce54069ecc100a`.
- Base config hash `1b252cb9de1f9b70301bbb4feb660aed36ec888b030a5979c0ff59ac0fa6d64f`; versions {'sim_version': 'sim-1.0', 'policy_version': 'pol-1.0', 'metric_version': 'metric-1.0', 'proxy_version': 'proxy_v1', 'stream_schema': 'stream-1'}.
- Seeds: {'dev': 1101, 'train': 2202, 'calib': 3303, 'eval': 4404, 'stress': 5505, 'sens': 6606, 'pilot': 7707, 'nonce_key': 918273645}.
- Runtime budget: projected PRIMARY 0.17 h with 4 workers at K=32: no K reduction needed.

## Exclusions

only prespecified technical-validity failures, with an audit record; all runs reported.
