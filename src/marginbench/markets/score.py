"""Proper scores and the paired evidence gate for Track M.

Per settled pair: the quantile score QS = 2 x mean pinball loss over the forecast's levels (it
approaches CRPS as the levels get dense; Gneiting and Raftery 2007) and the hit of each central
interval the levels define. Lower QS is better. A comparison pairs two forecasters on the same
(symbol, target session), averages the QS difference per session, and bootstraps sessions in
moving blocks. The gate is hvega's SPEC 12.3 rule: a challenger passes only with n sessions at or
above ``min_n`` and the whole 90% interval of (incumbent QS - challenger QS) above 0.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np

from marginbench.environment.randomness import generator_from_seed, key_to_seed
from marginbench.markets import tape

BP = 1e4


def pinball(tau: float, q: float, y: float) -> float:
    return ((1.0 if y < q else 0.0) - tau) * (q - y)


def quantile_score(levels: list[float], qs: list[float], y: float) -> float:
    return 2.0 * float(np.mean([pinball(a, q, y) for a, q in zip(levels, qs)]))


def hits(levels: list[float], qs: list[float], y: float) -> dict[str, int]:
    """Central-interval hits for each symmetric level pair (a, 1 - a) present, keyed by width."""
    by = {round(a, 6): q for a, q in zip(levels, qs)}
    out = {}
    for a, lo in by.items():
        hi = by.get(round(1.0 - a, 6))
        if a < 0.5 and hi is not None:
            out[f"{1.0 - 2.0 * a:.2f}"] = int(lo <= y <= hi)
    return out


def score_row(fc: dict[str, Any], out: dict[str, Any], reason: str | None) -> dict[str, Any]:
    row: dict[str, Any] = {
        "v": tape.VERSION, "forecast_id": fc["id"], "forecaster": fc["forecaster"],
        "task": fc["task"], "symbol": fc["symbol"], "base_session": fc["base_session"],
        "target_session": out["target_session"], "outcome_id": out["id"],
        "visibility": fc["visibility"], "valid": reason is None, "reason": reason,
    }
    if reason is None:
        row["qs"] = quantile_score(fc["levels"], fc["quantiles"], out["y"])
        row["hits"] = hits(fc["levels"], fc["quantiles"], out["y"])
    return row


def _paired(rows: list[dict[str, Any]], inc: str, ch: str) -> tuple[list[str], np.ndarray, float]:
    """Sessions, the per-session mean of (QS inc - QS ch), and the incumbent's mean QS on those pairs."""
    by: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    for r in rows:
        if r["valid"] and r["forecaster"] in (inc, ch):
            by[(r["target_session"], r["symbol"])][r["forecaster"]] = r["qs"]
    per_session: dict[str, list[float]] = defaultdict(list)
    inc_qs: list[float] = []
    for (sess, _sym), d in by.items():
        if inc in d and ch in d:
            per_session[sess].append(d[inc] - d[ch])
            inc_qs.append(d[inc])
    sessions = sorted(per_session)
    diffs = np.array([np.mean(per_session[s]) for s in sessions], dtype=float)
    return sessions, diffs, float(np.mean(inc_qs)) if inc_qs else 0.0


def compare(rows: list[dict[str, Any]], inc: str, ch: str, task: str, cfg: dict[str, Any] | None) -> dict[str, Any]:
    """The evidence row for (incumbent, challenger): hvega SPEC 12.3's shape."""
    sessions, d, _ = _paired(rows, inc, ch)
    ev: dict[str, Any] = {
        "task": task, "objective": "quantile score (lower is better)", "incumbent": inc,
        "challenger": ch, "n": len(sessions), "first": sessions[0] if sessions else None,
        "last": sessions[-1] if sessions else None,
        "mean_diff_bp": float(d.mean() * BP) if len(d) else None, "ci90_bp": None,
    }
    if cfg is None:
        ev.update(state="off", text="gate off (score: null)")
        return ev
    min_n = cfg.get("min_n")
    if min_n is None or len(d) < int(min_n):
        ev.update(state="collecting", text=f"n {len(d)} < {min_n}" if min_n is not None else "min_n off")
        return ev
    b = max(1, int(cfg.get("block") or 1))
    draws = int(cfg.get("draws") or 2000)
    level = float(cfg.get("ci") or 0.90)
    g = generator_from_seed(key_to_seed(f"markets|bootstrap|{task}|{inc}|{ch}|{len(d)}|{sessions[-1]}"))
    n = len(d)
    k = -(-n // b)
    starts = g.integers(0, n - b + 1, size=(draws, k))
    idx = (starts[:, :, None] + np.arange(b)[None, None, :]).reshape(draws, -1)[:, :n]
    means = d[idx].mean(axis=1)
    lo, hi = np.quantile(means, [(1 - level) / 2, 1 - (1 - level) / 2])
    ev["ci90_bp"] = [float(lo * BP), float(hi * BP)]
    passed = bool(lo > 0)
    ev.update(
        state="pass" if passed else "fail",
        text=(f"{ch} beats {inc}: CI [{lo * BP:+.2f}, {hi * BP:+.2f}] bp above 0, n {n}" if passed
              else f"CI [{lo * BP:+.2f}, {hi * BP:+.2f}] bp {'straddles' if hi > 0 else 'below'} 0, n {n}"),
    )
    return ev


def leaderboard(rows: list[dict[str, Any]], cfg: dict[str, Any]) -> dict[str, Any]:
    ref = cfg.get("reference")
    score_cfg = cfg.get("score")
    out: dict[str, Any] = {"reference": ref, "tasks": {}}
    for task in sorted({r["task"] for r in rows}):
        tr = [r for r in rows if r["task"] == task]
        names = sorted({r["forecaster"] for r in tr})
        table = []
        for f in names:
            fr = [r for r in tr if r["forecaster"] == f and r["valid"]]
            inv = sum(1 for r in tr if r["forecaster"] == f and not r["valid"])
            cov: dict[str, list[int]] = defaultdict(list)
            for r in fr:
                for w, h in r["hits"].items():
                    cov[w].append(h)
            table.append({
                "forecaster": f, "n": len(fr), "invalid": inv, "symbols": len({r["symbol"] for r in fr}),
                "visibility": sorted({r["visibility"] for r in tr if r["forecaster"] == f}),
                "qs_bp": float(np.mean([r["qs"] for r in fr]) * BP) if fr else None,
                "coverage": {w: float(np.mean(h)) for w, h in sorted(cov.items())},
            })
        if ref in names:
            for t in table:
                _, d, ref_mean = _paired(tr, ref, t["forecaster"])
                ok = len(d) and t["forecaster"] != ref and ref_mean > 0
                t["skill_vs_ref"] = float(d.mean() / ref_mean) if ok else None
        pairs = [(ref, f) for f in names if ref in names and f != ref]
        pairs += [tuple(p) for p in (cfg.get("compare") or []) if p[0] in names and p[1] in names]
        out["tasks"][task] = {
            "table": sorted(table, key=lambda t: (t["qs_bp"] is None, t["qs_bp"] or 0.0)),
            "evidence": [compare(tr, a, b, task, score_cfg) for a, b in dict.fromkeys(pairs)],
        }
    return out


def _f(x: float | None, spec: str) -> str:
    return "" if x is None else format(x, spec)


def markdown(lb: dict[str, Any], title: str) -> str:
    lines = [f"# {title}", ""]
    for task, t in lb["tasks"].items():
        lines += [
            f"## {task}", "",
            f"| Forecaster | symbols | n | QS (bp) | Skill vs {lb['reference']} | 50% cov | 90% cov | invalid |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for r in t["table"]:
            c = r["coverage"]
            lines.append(
                f"| {r['forecaster']} | {r['symbols']} | {r['n']} | {_f(r['qs_bp'], '.2f')} | {_f(r.get('skill_vs_ref'), '+.1%')} "
                f"| {_f(c.get('0.50'), '.0%')} | {_f(c.get('0.90'), '.0%')} | {r['invalid']} |"
            )
        lines += [
            "", "| Incumbent | Challenger | n | mean diff (bp) | 90% CI (bp) | gate |", "|---|---|---|---|---|---|",
        ]
        for e in t["evidence"]:
            ci = e["ci90_bp"]
            ci_s = "" if ci is None else f"[{ci[0]:+.2f}, {ci[1]:+.2f}]"
            lines.append(
                f"| {e['incumbent']} | {e['challenger']} | {e['n']} | {_f(e['mean_diff_bp'], '+.2f')} "
                f"| {ci_s} | {e['state']}: {e['text']} |"
            )
        lines.append("")
    lines.append(
        "QS is 2 x mean pinball loss in basis points of log return; lower is better. QS pools the "
        "symbols a forecaster covers, so compare forecasters by Skill, which is the share of the "
        "reference's QS a forecaster removes on the same (symbol, session) pairs. A gate passes only "
        "when the whole 90% interval of (incumbent QS - challenger QS) is above 0 with n >= min_n."
    )
    return "\n".join(lines) + "\n"
