# Track M REPLAY, last 500 sessions (point-in-time backtest, NOT forward evidence)

## ret1d

| Forecaster | symbols | n | QS (bp) | Skill vs rw20 | 50% cov | 90% cov | invalid |
|---|---|---|---|---|---|---|---|
| vix | 1 | 500 | 37.10 | +0.2% | 69% | 97% | 0 |
| garch11 | 6 | 3000 | 42.51 | +1.4% | 55% | 90% | 0 |
| ewma94 | 6 | 3000 | 42.70 | +1.0% | 54% | 89% | 0 |
| rw20 | 6 | 3000 | 43.11 |  | 53% | 88% | 0 |

| Incumbent | Challenger | n | mean diff (bp) | 90% CI (bp) | gate |
|---|---|---|---|---|---|
| rw20 | ewma94 | 500 | +0.41 | [+0.11, +0.72] | pass: ewma94 beats rw20: CI [+0.11, +0.72] bp above 0, n 500 |
| rw20 | garch11 | 500 | +0.60 | [+0.29, +0.97] | pass: garch11 beats rw20: CI [+0.29, +0.97] bp above 0, n 500 |
| rw20 | vix | 500 | +0.06 | [-1.08, +1.21] | fail: CI [-1.08, +1.21] bp straddles 0, n 500 |
| vix | garch11 | 500 | +0.63 | [-0.21, +1.47] | fail: CI [-0.21, +1.47] bp straddles 0, n 500 |

QS is 2 x mean pinball loss in basis points of log return; lower is better. QS pools the symbols a forecaster covers, so compare forecasters by Skill, which is the share of the reference's QS a forecaster removes on the same (symbol, session) pairs. A gate passes only when the whole 90% interval of (incumbent QS - challenger QS) is above 0 with n >= min_n.
