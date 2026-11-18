# Track M leaderboard (forward: every forecast committed before its outcome)

## ret1d

| Forecaster | symbols | n | QS (bp) | Skill vs rw20 | 50% cov | 90% cov | invalid |
|---|---|---|---|---|---|---|---|
| vix | 1 | 2 | 36.87 | -3.6% | 50% | 100% | 0 |
| ewma94 | 6 | 12 | 48.75 | +1.1% | 50% | 92% | 0 |
| garch11 | 6 | 12 | 48.76 | +1.1% | 50% | 92% | 0 |
| rw20 | 6 | 12 | 49.29 |  | 50% | 92% | 0 |
| hvega-har-fhs | 6 | 12 | 50.72 | -2.9% | 50% | 83% | 0 |
| hvega-har-norm | 6 | 6 | 59.52 | -7.2% | 50% | 83% | 0 |

| Incumbent | Challenger | n | mean diff (bp) | 90% CI (bp) | gate |
|---|---|---|---|---|---|
| rw20 | ewma94 | 2 | +0.54 |  | collecting: n 2 < 30 |
| rw20 | garch11 | 2 | +0.53 |  | collecting: n 2 < 30 |
| rw20 | hvega-har-fhs | 2 | -1.43 |  | collecting: n 2 < 30 |
| rw20 | hvega-har-norm | 1 | -3.99 |  | collecting: n 1 < 30 |
| rw20 | vix | 2 | -1.28 |  | collecting: n 2 < 30 |
| vix | garch11 | 2 | +3.30 |  | collecting: n 2 < 30 |
| vix | hvega-har-fhs | 2 | +5.04 |  | collecting: n 2 < 30 |
| hvega-har-norm | hvega-har-fhs | 1 | +1.19 |  | collecting: n 1 < 30 |

QS is 2 x mean pinball loss in basis points of log return; lower is better. QS pools the symbols a forecaster covers, so compare forecasters by Skill, which is the share of the reference's QS a forecaster removes on the same (symbol, session) pairs. A gate passes only when the whole 90% interval of (incumbent QS - challenger QS) is above 0 with n >= min_n.
