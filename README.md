# MarginBench

A falsifiable synthetic benchmark for one question: **when a decision policy that beats the current operating baseline on a declared operational proxy replaces that baseline, does long-horizon operator value go up, stay the same, or go down, and under which declared conditions?**

The setting is a property-maintenance operator: tenants report repairs, the operator triages, dispatches contractors, verifies or closes, and earns a management fee from owners who may terminate the contract. The dashboard proxy rewards fast first closure at low operating cost. Business value is the operator's discounted cash contribution over 270 days.

- Specification: [`SPEC.md`](SPEC.md) (binding). Choices where it was silent: [`DECISIONS.md`](DECISIONS.md).
- Plan: [`EXPERIMENT_PLAN.md`](EXPERIMENT_PLAN.md), generated from `configs/plan.yaml`, committed as `prereg: plan v1` before any locked run.
- Results: [`RESULTS_SUMMARY.md`](RESULTS_SUMMARY.md), [`CLAIMS.md`](CLAIMS.md), and a self-contained `report.html` in each `results/<experiment>/` directory.
- [`ASSUMPTIONS.md`](ASSUMPTIONS.md) lists every mechanism and parameter (all synthetic). [`LIMITATIONS.md`](LIMITATIONS.md) lists what the design cannot show.

## Why a proxy can diverge from value, in principle

A proxy is a function of what is observed early. Value depends on what happens later, including things the proxy cannot see. The two diverge when (1) the objective is misaligned, (2) state is only partly observed, (3) the policy's model is wrong, (4) the planning horizon is short, (5) actions change what gets measured (closing without verification suppresses callbacks), (6) actions change future workload (unresolved repairs come back), (7) consequences are delayed or rare (severe losses, contract terminations), and (8) the contract decides who pays (owners pay invoices; operators pay credits and negligent-loss shares). MarginBench can switch each mechanism off and measure what changes. It never assumes a reversal; it estimates one.

## Environment

Discrete-event simulation in integer minutes. 20 properties × 10 units, 4 contractors (one cheap and unreliable, one fast and unreliable, one expensive and reliable), Poisson arrivals with seasonal HVAC, noisy reported severity, contractor reports that can falsely claim completion, noisy verification, tenant callbacks, SLA credits, severe losses while repairs stay unresolved, and owner termination hazards driven by callbacks, breaches, losses and owner spend. Every state field has a visibility class (PUBLIC, OBSERVABLE_AFTER_EVENT, LATENT, EVALUATOR_ONLY); policies see only an allowlisted observation. All randomness is keyed by SHA-256 of (version, partition, seed, replication, mechanism, entity, index), so every policy arm in a replication faces the same arrivals and the same repair luck.

Time: warm-up days 0-29 (P0 decides for every arm), decision window days 30-119 (the policy under test decides everything), continuation and maturation days 120-299 (P0 decides, except that the tested policy keeps each decision-cohort request until its first closure). The proxy is read at day 133; value is summed over days 30-299, discounted at 10% a year.

## Policies

| ID | Objective | Horizon | Notes |
|---|---|---|---|
| P0 | operating baseline rules | - | cheapest contractor with p̂ ≥ 0.75 that meets SLA; verify moderate; primary comparator |
| P1 | proxy | myopic | Monte Carlo action valuation, K = 32 |
| P2 | proxy | 60 days | **primary arm** |
| P3 | economic (operator cash minus retention term) | myopic | matched to P1 |
| P4 | economic | 60 days | matched to P2 |
| P5 | economic, risk-constrained | 60 days | matched to P4; relative loss/SLA caps, always-legal fallback |
| P6 | economic with true parameters and latent state | 60 days | **NON-DEPLOYABLE DIAGNOSTIC**, never in confirmatory results |

All feasible policies share one frozen estimator M trained only on observable history, the same rollout rule, the same K, and the same Monte Carlo seeds.

## Install and run

```bash
uv sync --frozen --extra test          # or: pip install -r requirements.lock && pip install -e .
uv run python -m pytest -q             # includes the frozen-test hash check
uv run marginbench smoke               # one dev replication of every policy
uv run marginbench train               # regenerate history and refit M (models/estimator_v1.json)
uv run marginbench prereg              # calib materiality and power -> configs/plan.yaml
scripts/evaluate.sh                    # every locked run, then the audit (refuses a dirty tree)
uv run marginbench report --results results/primary --output .
```

Exit codes: 0 for a valid run whatever the scientific result, 2 INVALID, 3 UNVERIFIED, 4 RESOURCE_LIMIT.

## Reproduce

```bash
uv run marginbench reproduce --manifest results/primary/run_manifest.json
```

This re-runs replication 0 for every arm and compares the canonical SHA-256 of its event stream and ledger with the stored hashes.

## What the results can and cannot support

They can support statements of the form "under configuration X, P2 raised the proxy and lowered (or raised, or did not change) simulated operator contribution relative to P0", with a preregistered interval and materiality band (Level 1), and, where the sensitivity design and ablations agree, statements about this model family (Level 2). They cannot support any statement about real operators, real contractors or real tenants (Level 3 is out of scope), and no share of sensitivity points is a real-world probability.

## How to read null and opposite results

Every contrast is classified, in order, as INVALID, UNVERIFIED, PROXY_NOT_IMPROVED, REVERSAL_SUPPORTED (STRONG if the whole interval lies beyond −m), ALIGNMENT_SUPPORTED, EQUIVALENCE_SUPPORTED (TOST within ±m) or INCONCLUSIVE; value contrasts use VALUE_HIGHER/VALUE_LOWER. An EQUIVALENCE or ALIGNMENT result for the primary contrast is a finding, not a failure: it says that in this declared world, chasing the proxy did not cost value. INCONCLUSIVE means the preregistered sample could not separate the effect from zero and from ±m. The pipeline produces every class without code changes; tests in `tests/integration/test_outcome_paths.py` exercise each one.
