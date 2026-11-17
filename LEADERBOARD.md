# Track M leaderboard (forward: every forecast committed before its outcome)

## ret1d

| Forecaster | symbols | n | QS (bp) | Skill vs rw20 | 50% cov | 90% cov | invalid |
|---|---|---|---|---|---|---|---|
| vix | 1 | 1 | 39.83 | +0.2% | 0% | 100% | 0 |
| ewma94 | 6 | 6 | 42.01 | +2.4% | 50% | 100% | 0 |
| garch11 | 6 | 6 | 42.79 | +0.6% | 50% | 100% | 0 |
| rw20 | 6 | 6 | 43.05 |  | 50% | 100% | 0 |
| hvega-har-fhs | 6 | 6 | 43.10 | -0.1% | 50% | 83% | 0 |

| Incumbent | Challenger | n | mean diff (bp) | 90% CI (bp) | gate |
|---|---|---|---|---|---|
| rw20 | ewma94 | 1 | +1.03 |  | collecting: n 1 < 30 |
| rw20 | garch11 | 1 | +0.25 |  | collecting: n 1 < 30 |
| rw20 | hvega-har-fhs | 1 | -0.05 |  | collecting: n 1 < 30 |
| rw20 | vix | 1 | +0.07 |  | collecting: n 1 < 30 |
| vix | garch11 | 1 | +0.41 |  | collecting: n 1 < 30 |

QS is 2 x mean pinball loss in basis points of log return; lower is better. QS pools the symbols a forecaster covers, so compare forecasters by Skill, which is the share of the reference's QS a forecaster removes on the same (symbol, session) pairs. A gate passes only when the whole 90% interval of (incumbent QS - challenger QS) is above 0 with n >= min_n.
