# Next: horizon-matched volatility challengers for Track M

Owner, 2026-11-19: "yup do that", in reply to a proposal to test the RiskMetrics λ = 0.94 convention instead of inheriting it. Status: open. Nothing here is built.

## Why

`ewma94` (`configs/markets.yaml`) uses λ = 0.94. RiskMetrics (J.P. Morgan, 1994–96) picked that value as one decay for all series, to minimize one-day-ahead variance error, and used 0.97 for monthly data. It is a convention, not a fit to these symbols. Its properties:

- half-life ln 0.5 / ln 0.94 ≈ 11.2 sessions;
- mean lag 1/(1 − λ) ≈ 16.7 sessions;
- 99% of the weight in the last ≈ 74 sessions;
- IGARCH with ω = 0, so its forecast is flat at every horizon and never reverts to the mean.

`ret1d` is the horizon 0.94 was tuned for, so `ewma94` is a fair baseline there. It went level with `garch11` (+1.1% skill vs `rw20`) over the first two sessions, which is noise. The claim worth testing is the one at option horizons: that a decay fixed at 0.94 is too slow for one-day vol, too fast against 30-day IV, and beaten out of sample by HAR-RV or GARCH(1,1). Track M doesn't score that yet.

## Constraints (do not break)

- `ewma94` already has committed forecasts and scores. Never edit it or its parameters. Each idea is a new forecaster name or a new task (AGENTS rule 3 in spirit; hvega AGENTS rule 16, "nobody edits one that has rows").
- Every new key is optional, and `null` turns it off (AGENTS rule 8).
- Forecasts are issued before the target session opens (D-53), and REPLAY results are never forward evidence.
- Raw Yahoo bars are never stored here (D-49). OHLC is already on the tape observations (`yahoo.py` keeps open, high, low and close), but `forecasters.Sigma` only sees returns `r`. A range estimator therefore needs an interface change, recorded in DECISIONS.md.
- Every number in a doc comes from a results artifact (AGENTS rule 4).

## Work

1. **`ewma_hl` kind.** `ewma` with `half_life` in sessions, λ = 0.5^(1/half_life). Add forecasters for `ret1d` at half-lives of 2, 5 and 11, where 11 ≈ λ 0.94 serves as a consistency check against `ewma94`. Starting rule for a horizon of h sessions: half-life ≈ h/2. That rule is a heuristic to test, not a claim.
2. **Horizon task `rv21`** (and optionally `rv5`). The target is the realized vol of the next 21 sessions' close-to-close log returns, annualized over 252 sessions, scored by the same QS on its quantiles. Every forecaster maps its sigma to the horizon its own way: `ewma`/`ewma_hl` flat, `garch11` with mean reversion to its unconditional variance, `rw` flat, `vix` as is (30 calendar days ≈ 21 sessions). Add `compare` rows `[vix, garch11]`, `[vix, ewma94]` and `[ewma94, <best ewma_hl>]` for `rv21`. This task is where the "no mean reversion" claim gets tested.
3. **Optional: a range estimator** (Parkinson, then Yang-Zhang) for `ret1d`, after the interface change in "Constraints". Record it as a numbered DECISIONS entry.
4. Run `marginbench markets replay` for each new forecaster and task, label the results REPLAY, and update `docs/TRACK-M.md` sections 3–4 for the new task.

## Done when

- `configs/markets.yaml` has the `ewma_hl` forecasters and the `rv21` task. Each has a test of its `null` path, and `scripts/test.sh` passes.
- On `markets-ledger`, `commitments`/`forecasts` hold rows for the new forecasters on `rv21` and `ret1d`, recorded before each target's open, for at least one forward session.
- LEADERBOARD.md shows the new `compare` rows. Each is `collecting` until n ≥ `score.min_n` (30), and none is read as evidence before then.
- This file is deleted in the PR that lands items 1–2, or it is left with only the unfinished items.
