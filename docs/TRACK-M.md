# Track M: MarginBench on real markets

Status: v1, 2026-11-16. Owner's direction, 2026-11-16: MarginBench should keep becoming more useful by taking in the data that hvega and underlying-analyzer-reboot see every day, so that hvega can be hill-climbed against it and both improve together. Privacy choice A (owner, 2026-11-16): this public repo gets the code, the task definitions and the scores on public market data. Account data and hvega's raw forecasts stay private, and only their hashes appear here.

## 1. The question

The synthetic benchmark asks whether a policy that beats a proxy also raises long-horizon value, in a declared world. Track M asks the same question of real forecasters against real outcomes: does a forecaster that looks better actually predict the market better, measured only on outcomes that did not exist when it spoke?

Three rules make that answerable:

1. **Forecasts before outcomes.** A forecast counts only if it was issued, and for a private forecast its hash was published, before the target session opened. This is the prequential principle (Dawid 1984), and it is what ForecastBench does for LLM forecasters. It makes every new day a held-out test that cannot leak.
2. **Proper scores.** A forecaster is scored on its whole predictive distribution, not on a point (Gneiting and Raftery 2007). A forecaster cannot improve its expected score by misreporting what it believes.
3. **The gate is hvega's.** A challenger replaces an incumbent only when the bootstrap 90% interval of the paired score difference lies above 0 with n ≥ `score.min_n` sessions (hvega SPEC 12.3). The track produces that evidence row, and hvega's evolution ledger consumes it.

## 2. The two envelopes (`src/marginbench/markets/tape.py`)

Every producer (Yahoo here; hvega's Robinhood reads, MCP calls and pushes; underlying-analyzer's data reads) writes the same **Observation**:

| field | meaning |
|---|---|
| `v` | 1 |
| `kind` | `bar.daily`, `dividend`, `quote`, `position`, `push`, ... |
| `source` | the call that produced it (`yahoo.chart.v8`, `robinhood.mcp.get_equity_quotes`) |
| `producer` | the code that wrote it, with a version (`hvega.tape@1`) |
| `symbol` | ticker or null |
| `observed_at` | UTC time the fact was true (`...Z`) |
| `visibility` | `public` or `private`; private rows never enter this repo |
| `payload` | the fact |
| `id` | sha256 of the canonical JSON of every field except `id` and `recorded_at` |
| `recorded_at` | optional: when it was written. Not hashed, so the same fact recorded twice is one row |

A **Forecast** is `{v, task, forecaster, symbol, issued_at, base_session, levels, quantiles, inputs_sha256, visibility, id}`: a predictive distribution as quantiles at strictly increasing levels in (0, 1), non-crossing, plus a hash of the exact inputs it used.

A **Commitment** is the public trace of a private forecast: `{forecast_id, task, forecaster, symbol, base_session, issued_at, recorded_at}`. It contains no quantiles and no inputs.

Canonical JSON is `marginbench.hashing.canonical_json` (sorted keys, no whitespace, shortest float repr, no NaN). hvega's stdlib writer follows the same rule, and the shared fixture `tests/markets/fixtures/envelope_v1.json` pins the ids in both repos.

## 3. Task `ret1d`

- **Target:** the total log return from the base session's close to the next final session's close, ln((C_T + D_T) / C_B), where D_T is the dividend going ex on T. "Next" means the next session in the data, so no holiday calendar has to be maintained.
- **Final:** a session is final `settle_buffer_min` minutes after its 16:00 ET close. A bar still forming is never stored. Early-close days wait until the normal close plus the buffer.
- **Symbols:** SPY, QQQ, IWM, DIA, TLT, GLD (`configs/markets.yaml`).
- **Forecast:** quantiles at 2.5, 5, 10, 25, 50, 75, 90, 95 and 97.5%.
- **Score:** QS = 2 × mean pinball loss over the levels, in basis points (it approaches CRPS as the levels get dense). The leaderboard also reports 50% and 90% central-interval coverage.
- **Baselines:** `rw20` (20-day sample sd, the reference), `ewma94` (RiskMetrics), `garch11` (Gaussian MLE on 750 days) and `vix` (the ^VIX close / 100 / √252, SPY only). That last one is the market's own risk-neutral 30-day forecast, so it carries the variance risk premium. Beating it is the test that matters.

## 4. The nightly loop (`marginbench markets nightly --ledger DIR [--private DIR]`)

1. **Observe:** one Yahoo chart call per universe symbol. A failed call is a named hold for that symbol, the command exits 4, and the symbol is never treated as having no data.
2. **Settle:** every forecast without a score, public or (with `--private`) private, whose target is final gets an outcome row and a score row. A late forecast, or a private one with no commitment published before the open, is scored `valid: false` with the reason and never enters a comparison.
3. **Issue:** each forecaster forecasts the next session from data up to the last final session. Nothing is issued during a regular session, because such a forecast would be invalid.
4. **Publish:** `leaderboard.json` and `LEADERBOARD.md` are rebuilt from `scores.jsonl`, and a receipt is written to `receipts/<date>.json` (code commit, config hash, observation-set hash, file hashes, holds, counts).

The public ledger lives on the `markets-ledger` branch of this repo: append-only `forecasts`, `commitments`, `outcomes` and `scores` (JSON lines), plus the derived leaderboard and receipts. Raw Yahoo bars are not stored here (DECISIONS D-49). The durable raw tape lives on hvega's private `tape` branch.

`marginbench markets replay` runs the same baselines point-in-time over the last N sessions. Its inputs contain no hindsight, but nothing in it was committed in advance, so it is labeled REPLAY and is never forward evidence. Its role is to calibrate expectations and test the pipeline.

## 5. How hvega enters

1. hvega writes its forecasts as Forecast rows with `visibility: private` on its private `tape` branch.
2. Before the target opens, it publishes their commitments: `marginbench markets commit --file F --ledger DIR`.
3. The nightly runs with `--private` pointing at hvega's tape, and scores them next to the baselines. Only the score rows (forecast id, QS, hits) become public.
4. The paired evidence row (`leaderboard.json` → `evidence`) is the input to hvega's 12.3 gate. A parameter changes in hvega only when that row says `pass`.

## 6. What this cannot show

- One-day returns of six liquid ETFs are one slice of what hvega forecasts. Intraday vol, touch probabilities, regime transitions and option P&L are later tasks, each a new task block with its own target and score.
- Normal quantiles are a simplification of the baselines (D-51). The coverage columns show where it fails.
- Yahoo data is unofficial. A revision after settlement does not rewrite an outcome (first write wins), and the receipt's observation hash records what was read.
- REPLAY numbers are a backtest. Only the forward ledger is evidence.
