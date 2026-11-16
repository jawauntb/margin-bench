# Track M leaderboard (forward: every forecast committed before its outcome)

QS is 2 x mean pinball loss in basis points of log return; lower is better. QS pools the symbols a forecaster covers, so compare forecasters by Skill, which is the share of the reference's QS a forecaster removes on the same (symbol, session) pairs. A gate passes only when the whole 90% interval of (incumbent QS - challenger QS) is above 0 with n >= min_n.
