"""Fit the estimator M on observable history only (SPEC 10.2).

Regularization is chosen on the calibration partition; final models are fit on train.
Every censoring and selection rule is listed in DECISIONS.md.
"""

from __future__ import annotations

import math
import warnings
from collections import defaultdict
from typing import Any

import numpy as np
from scipy import stats
from sklearn.linear_model import LogisticRegression, PoissonRegressor

from marginbench.estimation.estimator import CATS, CONTRACTORS, SEVS, FrozenEstimator, success_features

DAY = 1440
MATURITY_DAYS = 60
C_GRID = (0.01, 0.1, 1.0, 10.0)
LC_OUTER_ITERS = 40
LC_INNER_ITERS = 100
ALPHA_GRID = (0.0, 1e-4, 1e-3, 1e-2)
WINDOWS = {"cb": 90, "br": 90, "sl": 365, "oc": 90}


# ------------------------------------------------------------------------------- parsing
def parse_dataset(ds: dict[str, Any]) -> dict[str, Any]:
    """Per-request observable histories from one portfolio's observable log."""
    props = ds["properties"]
    hist_end = ds["history_days"] * DAY
    reqs: dict[str, dict[str, Any]] = {}
    acts = iter(ds["actions"])
    losses: list[dict[str, Any]] = []
    infos: list[tuple[str, str]] = []
    prop_logs: dict[str, dict[str, list[tuple[int, float]]]] = {p: {"cb": [], "br": [], "sl": [], "oc": []} for p in props}
    notices: dict[str, int] = {}
    for ev in ds["events"]:
        t, typ, rid, pid, d = ev["tick"], ev["type"], ev["request_id"], ev["property_id"], ev["data"]
        if typ == "ARRIVAL":
            reqs[rid] = {"pid": pid, "cat": d["category"], "sev": d["reported_severity"], "arrival": t,
                         "attempts": [], "open_since": t, "open": [], "q": props[pid]["q_obs"]}
            continue
        if typ == "TERMINATION_NOTICE":
            notices[pid] = t // DAY
            continue
        if typ == "CONTRACT_TERMINATED":  # observable: the operator stops serving the property
            for r in reqs.values():
                if r["pid"] == pid and r["open_since"] is not None:
                    r["open"].append((r["open_since"], t, r["sev"]))
                    r["open_since"] = None
            continue
        if typ == "SLA_BREACH":
            prop_logs[pid]["br"].append((t // DAY, 1.0))
        if typ == "SEVERE_LOSS":
            prop_logs[pid]["sl"].append((t // DAY, 1.0))
        if rid is None or rid not in reqs:
            if typ == "ACTION":
                next(acts)
            continue
        r = reqs[rid]
        if typ == "ACTION":
            a = next(acts)
            assert a["request_id"] == rid and a["type"] == d["action_type"]
            at = a["type"]
            if at in ("dispatch", "redispatch", "escalate"):
                r["attempts"].append({"c": a["contractor"], "k": r["cat"], "sev": r["sev"], "j": len(r["attempts"]),
                                      "q": r["q"], "dispatch": t, "escalated": at == "escalate",
                                      "reopened": r.get("reopened", False), "start": None, "complete": None,
                                      "report": None, "verify": None, "closed": None, "cu": None, "callback": None})
            elif at == "close":
                if r["attempts"]:
                    att = r["attempts"][-1]
                    att["closed"] = t
                    att["cu"] = a["stage"] == "WORK_REPORTED"
                if r["open_since"] is not None:
                    r["open"].append((r["open_since"], t, r["sev"]))
                    r["open_since"] = None
        elif typ == "WORK_START":
            r["attempts"][-1]["start"] = t
        elif typ == "WORK_COMPLETE":
            r["attempts"][-1]["complete"] = t
            r["attempts"][-1]["report"] = d["report"]
            prop_logs[pid]["oc"].append((t // DAY, d["invoice_cents"] / 100.0))
        elif typ == "VERIFY_RESULT":
            r["attempts"][-1]["verify"] = d["result"]
        elif typ == "CALLBACK":
            prop_logs[pid]["cb"].append((t // DAY, 1.0))
            if r["attempts"] and r["attempts"][-1]["closed"] is not None and r["attempts"][-1]["callback"] is None:
                r["attempts"][-1]["callback"] = t
            r["open_since"] = t
            r["reopened"] = True
        elif typ == "INFO_ARRIVES":
            infos.append((r["sev"], d["reported_severity"]))
            r["sev"] = d["reported_severity"]
        elif typ == "SEVERE_LOSS":
            losses.append({"sev": r["sev"], "amount": d["owner_visible_amount_cents"] / 100.0})
        elif typ == "HANDOVER":
            if r["open_since"] is not None:
                r["open"].append((r["open_since"], t, r["sev"]))
                r["open_since"] = None
            r["handed_over"] = True
    for r in reqs.values():
        if r["open_since"] is not None:
            r["open"].append((r["open_since"], hist_end, r["sev"]))
    return {"requests": reqs, "losses": losses, "infos": infos, "prop_logs": prop_logs, "notices": notices,
            "hist_end": hist_end, "properties": props, "history_days": ds["history_days"]}


def _decode_feat(x: Any) -> tuple[str, str, str, int, float]:
    return (CONTRACTORS[int(np.argmax(x[0:4]))], CATS[int(np.argmax(x[4:8]))], SEVS[int(np.argmax(x[8:11]))],
            int(x[11]), float(x[12]))


def success_rows(parsed: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    """Labels observable only through verification or a callback; matured attempts only.
    Unverified attempts with no callback are excluded, not labeled successes."""
    X, y = [], []
    counts = {"attempts": 0, "immature": 0, "unlabeled_excluded": 0, "labeled": 0}
    for p in parsed:
        cutoff = p["hist_end"] - MATURITY_DAYS * DAY
        for r in p["requests"].values():
            for a in r["attempts"]:
                if a["complete"] is None:
                    continue
                counts["attempts"] += 1
                if a["complete"] > cutoff:
                    counts["immature"] += 1
                    continue
                label = None
                if a["verify"] == "fail":
                    label = 0
                elif a["callback"] is not None:
                    label = 0
                elif a["verify"] == "ok":
                    label = 1
                if label is None:
                    counts["unlabeled_excluded"] += 1
                    continue
                counts["labeled"] += 1
                X.append(success_features(a["c"], a["k"], a["sev"], a["j"], a["q"]))
                y.append(label)
    return np.asarray(X, dtype=float), np.asarray(y, dtype=int), counts


def _fit_logistic(Xtr, ytr, Xca, yca) -> tuple[LogisticRegression, float, list[dict[str, float]]]:
    best = None
    grid = []
    for C in C_GRID:
        m = LogisticRegression(C=C, max_iter=2000)
        m.fit(Xtr, ytr)
        pr = np.clip(m.predict_proba(Xca)[:, 1], 1e-9, 1 - 1e-9)
        ll = float(-np.mean(yca * np.log(pr) + (1 - yca) * np.log(1 - pr)))
        grid.append({"C": C, "calib_log_loss": ll})
        if best is None or ll < best[1]:
            best = (C, ll)
    assert best is not None
    m = LogisticRegression(C=best[0], max_iter=2000)
    m.fit(Xtr, ytr)
    return m, best[0], grid


def em_latent_class(rows: list[dict[str, Any]], iters: int = 400) -> dict[str, Any]:
    """Latent-class EM over matured attempts with the success model's p-hat as the prior.

    Observables per attempt: contractor report; verification result (if verified); and, if
    the attempt was closed, whether a callback arrived within the maturity window. The
    latent class is physical success. Rates (tc, fc, sens, spec, benign callback rate b,
    callback-given-failure rate per (reported severity, closed-unverified) cell) get Beta(1,1)
    posterior-mean M-steps. Callbacks identify failures, which makes sensitivity and
    specificity identifiable (DECISIONS D-21)."""
    p = np.array([r["p"] for r in rows])
    comp = np.array([r["report"] == "complete" for r in rows])
    ver = np.array([r["verify"] is not None for r in rows])
    vok = np.array([r["verify"] == "ok" for r in rows])
    closed = np.array([r["closed"] for r in rows])
    cb = np.array([r["callback"] for r in rows])
    cell = np.array([SEVS.index(r["sev"]) * 2 + int(r["cu"]) for r in rows])
    tc, fc, sens, spec, b = 0.95, 0.6, 0.8, 0.9, 0.03
    rho = np.full(6, 0.5)
    for _ in range(iters):
        rc = rho[cell]
        l1 = (p * np.where(comp, tc, 1 - tc) * np.where(ver, np.where(vok, spec, 1 - spec), 1.0)
              * np.where(closed, np.where(cb, b, 1 - b), 1.0))
        l0 = ((1 - p) * np.where(comp, fc, 1 - fc) * np.where(ver, np.where(vok, 1 - sens, sens), 1.0)
              * np.where(closed, np.where(cb, rc, 1 - rc), 1.0))
        w = l1 / np.maximum(l1 + l0, 1e-300)
        tc = (np.sum(w * comp) + 1) / (np.sum(w) + 2)
        fc = (np.sum((1 - w) * comp) + 1) / (np.sum(1 - w) + 2)
        spec = (np.sum(w * ver * vok) + 1) / (np.sum(w * ver) + 2)
        sens = (np.sum((1 - w) * ver * ~vok) + 1) / (np.sum((1 - w) * ver) + 2)
        b = (np.sum(w * closed * cb) + 1) / (np.sum(w * closed) + 2)
        for c in range(6):
            m = (cell == c) & closed
            rho[c] = (np.sum((1 - w[m]) * cb[m]) + 1) / (np.sum(1 - w[m]) + 2)
    rc = rho[cell]
    l1 = (p * np.where(comp, tc, 1 - tc) * np.where(ver, np.where(vok, spec, 1 - spec), 1.0)
          * np.where(closed, np.where(cb, b, 1 - b), 1.0))
    l0 = ((1 - p) * np.where(comp, fc, 1 - fc) * np.where(ver, np.where(vok, 1 - sens, sens), 1.0)
          * np.where(closed, np.where(cb, rc, 1 - rc), 1.0))
    loglik = float(np.sum(np.log(np.maximum(l1 + l0, 1e-300))))
    return {"tc": float(tc), "fc": float(fc), "sens": float(sens), "spec": float(spec), "benign_rate": float(b),
            "loglik": loglik,
            "rho_cells": [float(x) for x in rho], "n": int(len(rows)), "n_verified": int(ver.sum()),
            "n_closed": int(closed.sum()), "posterior_success": w}


def _trailing(arr: np.ndarray, window: int) -> np.ndarray:
    """out[d] = sum(arr[d-window : d]) (days d-window .. d-1)."""
    cs = np.concatenate([[0.0], np.cumsum(arr)])
    d = np.arange(arr.size)
    lo = np.maximum(d - window, 0)
    return cs[d] - cs[lo]


def contract_day_rows(parsed: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    X, y = [], []
    for p in parsed:
        n_days = p["history_days"]
        for pid, info in p["properties"].items():
            units = info["units"]
            arrs = {k: np.zeros(n_days) for k in WINDOWS}
            for k, log in p["prop_logs"][pid].items():
                for d, w in log:
                    if d < n_days:
                        arrs[k][d] += w
            f = {k: _trailing(arrs[k], WINDOWS[k]) for k in WINDOWS}
            f["cb"] = f["cb"] / units
            f["oc"] = f["oc"] / units / 100.0
            last = p["notices"].get(pid, n_days - 1)
            for d in range(0, min(last, n_days - 1) + 1):
                X.append([f["cb"][d], f["br"][d], f["sl"][d], f["oc"][d]])
                y.append(1 if (pid in p["notices"] and d == p["notices"][pid]) else 0)
    return np.asarray(X), np.asarray(y)


def _poisson_se(model: PoissonRegressor, X: np.ndarray) -> list[float]:
    Xd = np.column_stack([np.ones(len(X)), X])
    mu = model.predict(X)
    info = (Xd * mu[:, None]).T @ Xd
    n = len(X)
    info[1:, 1:] += n * model.alpha * np.eye(X.shape[1])
    try:
        cov = np.linalg.inv(info)
        return [float(math.sqrt(max(v, 0.0))) for v in np.diag(cov)]
    except np.linalg.LinAlgError:
        return [float("nan")] * Xd.shape[1]


def fit_estimator(train_ds: list[dict[str, Any]], calib_ds: list[dict[str, Any]]) -> tuple[FrozenEstimator, dict[str, Any]]:
    tr = [parse_dataset(d) for d in train_ds]
    ca = [parse_dataset(d) for d in calib_ds]
    report: dict[str, Any] = {}

    # 1. success model
    Xtr, ytr, ctr = success_rows(tr)
    Xca, yca, cca = success_rows(ca)
    sm, C, grid = _fit_logistic(Xtr, ytr, Xca, yca)
    succ = {"intercept": float(sm.intercept_[0]), "coef": [float(v) for v in sm.coef_[0]], "C": C,
            "features": "onehot(contractor A-D), onehot(category), onehot(reported sev), attempt_index, q_obs"}
    report["success"] = {"train_counts": ctr, "calib_counts": cca, "grid": grid, "C": C}
    est0 = FrozenEstimator({"success": succ})

    # 2-3. Joint latent-class fit (DECISIONS D-21). The selection-labeled model above
    # (SPEC 10.2) initializes p-hat; the latent-class EM then re-estimates the success
    # model with soft labels over all matured attempts, jointly with the report,
    # verification and callback rates. A fixed number of outer iterations, no tuning.
    rows: list[dict[str, Any]] = []
    Xall: list[list[float]] = []
    delays_l: list[float] = []
    n_imm_closures = 0
    n_closures = 0
    for p in tr:
        cutoff = p["hist_end"] - MATURITY_DAYS * DAY
        for r in p["requests"].values():
            for a in r["attempts"]:
                if a["closed"] is not None:
                    n_closures += 1
                    if a["closed"] > cutoff:
                        n_imm_closures += 1
                if a["complete"] is None or a["complete"] > cutoff:
                    continue
                closed = a["closed"] is not None and a["closed"] <= cutoff
                cbk = bool(closed and a["callback"] is not None and a["callback"] - a["closed"] <= MATURITY_DAYS * DAY)
                if cbk:
                    delays_l.append((a["callback"] - a["closed"]) / DAY)
                rows.append({"p": 0.0, "report": a["report"], "verify": a["verify"], "closed": closed, "callback": cbk,
                             "sev": a["sev"], "cu": bool(a["cu"]) if closed else False})
                Xall.append(success_features(a["c"], a["k"], a["sev"], a["j"], a["q"]))
    Xa = np.asarray(Xall, dtype=float)
    starts = {"flat_0.75": np.full(len(Xa), 0.75),
              "selection_labeled": np.asarray([est0.p_success(*_decode_feat(x)) for x in Xa])}
    fits = {}
    for name, pvec in starts.items():
        lc_model = sm
        trace = []
        for it in range(LC_OUTER_ITERS):
            for r, pi in zip(rows, pvec):
                r["p"] = float(pi)
            em = em_latent_class(rows, iters=LC_INNER_ITERS)
            w = em["posterior_success"]
            lc_model = LogisticRegression(C=C, max_iter=2000)
            lc_model.fit(np.vstack([Xa, Xa]), np.r_[np.ones(len(Xa)), np.zeros(len(Xa))], sample_weight=np.r_[w, 1 - w])
            pvec = lc_model.predict_proba(Xa)[:, 1]
            trace.append({k: em[k] for k in ("tc", "fc", "sens", "spec", "benign_rate", "loglik")})
        for r, pi in zip(rows, pvec):
            r["p"] = float(pi)
        em = em_latent_class(rows, iters=LC_INNER_ITERS)
        fits[name] = (em["loglik"], em, lc_model, trace)
    best_name = max(fits, key=lambda k: (fits[k][0], k))
    _, em, lc_model, trace = fits[best_name]
    report["success"]["latent_class_starts"] = {k: {"loglik": v[0], "final": v[3][-1]} for k, v in fits.items()}
    report["success"]["latent_class_selected"] = best_name
    w = em.pop("posterior_success")
    succ = {"intercept": float(lc_model.intercept_[0]), "coef": [float(v) for v in lc_model.coef_[0]], "C": C,
            "features": succ["features"], "method": "latent-class EM, initialized from the SPEC 10.2 selection-labeled model",
            "selection_labeled_init": {"intercept": succ["intercept"], "coef": succ["coef"]}}
    report["success"]["latent_class_trace"] = trace
    rv = {k: em[k] for k in ("tc", "fc", "sens", "spec", "n", "n_verified")}

    def cfeat(sev, cu):
        return [1.0 if sev == s else 0.0 for s in SEVS] + [1.0 if cu else 0.0]

    # callback model: weighted logistic regression of callback on (sev, cu) among matured
    # closed failures, failures weighted by their EM posterior (1 - w)
    Xc_l, yc_l, wc_l = [], [], []
    for r, wi in zip(rows, w):
        if r["closed"]:
            Xc_l.append(cfeat(r["sev"], r["cu"]))
            yc_l.append(int(r["callback"]))
            wc_l.append(float(1 - wi))
    Xc, yc, wc = np.asarray(Xc_l), np.asarray(yc_l), np.asarray(wc_l)
    cm = LogisticRegression(C=1.0, max_iter=2000)
    cm.fit(Xc, yc, sample_weight=np.maximum(wc, 1e-9))
    p_report = {s: {"1" if cu else "0": float(cm.predict_proba(np.asarray([cfeat(s, cu)]))[0, 1]) for cu in (False, True)}
                for s in SEVS}
    # calibration data for the audit: P(callback | matured closure) on calib, from the full model
    est1 = FrozenEstimator({"success": succ, "report_verify": rv, "callback": {"p_report": p_report}})
    cal_rows = []
    for p in ca:
        cutoff = p["hist_end"] - MATURITY_DAYS * DAY
        for r in p["requests"].values():
            for a in r["attempts"]:
                if a["closed"] is None or a["closed"] > cutoff or a["complete"] is None:
                    continue
                ph = est1.p_success(a["c"], a["k"], a["sev"], a["j"], a["q"])
                pi = est1.posterior_unresolved(1.0, ph, a["report"], a["verify"])
                pred = pi * est1.p_report(a["sev"], bool(a["cu"])) + (1 - pi) * em["benign_rate"]
                cbk = a["callback"] is not None and a["callback"] - a["closed"] <= MATURITY_DAYS * DAY
                cal_rows.append((pred, int(cbk)))
    Xcc = np.asarray([[x] for x, _ in cal_rows])
    ycc = np.asarray([y for _, y in cal_rows])
    report["callback"] = {"n_train_matured": int(len(yc)), "n_train_immature_excluded": n_imm_closures,
                          "n_train_closures": n_closures, "em": em, "cells": p_report}
    cl_tr = [(None, None, None, None, d * DAY) for d in delays_l]

    # 4. report delay (censored at the maturity window; documented)
    delays = np.asarray([dl / DAY for _, _, _, _, dl in cl_tr if dl is not None and dl > 0])
    if delays.size >= 5:
        shape, _, scale = stats.gamma.fit(delays, floc=0)
    else:
        shape, scale = 2.0, 4.0
    report["report_delay"] = {"n": int(delays.size), "censored_at_days": MATURITY_DAYS}

    # 5. lead time: empirical (start - dispatch) days per (contractor, category), regular jobs
    lead: dict[str, dict[str, list[float]]] = {c: {k: [] for k in CATS} for c in CONTRACTORS}
    for p in tr:
        for r in p["requests"].values():
            for a in r["attempts"]:
                if a["start"] is not None and not a["escalated"]:
                    lead[a["c"]][a["k"]].append((a["start"] - a["dispatch"]) / DAY)
    allv = [v for c in lead.values() for k in c.values() for v in k]
    overall = float(np.mean(allv)) if allv else 2.0
    lead_days = {c: {k: (float(np.mean(v)) if v else overall) for k, v in lead[c].items()} for c in CONTRACTORS}
    report["lead_days_n"] = {c: {k: len(v) for k, v in lead[c].items()} for c in CONTRACTORS}

    # 6. severe-loss hazard per reported severity: Poisson rate per expected unresolved
    # request-day, Gamma(1, 1000) shrinkage. Exposure: open days until the first work
    # completion, plus each later interval weighted by the smoothed P(unresolved): 1 until an
    # observed callback, else the posterior given no callback by the interval end (DECISIONS D-22).
    estx = FrozenEstimator({"success": succ, "report_verify": rv, "callback": {"p_report": p_report}})
    exposure = defaultdict(float)
    for p in tr:
        end = p["hist_end"]
        for r in p["requests"].values():
            first_c = next((a["complete"] for a in r["attempts"] if a["complete"] is not None), None)
            exposure[r["sev"]] += ((first_c if first_c is not None else end) - r["arrival"]) / DAY
            for a in r["attempts"]:
                if a["complete"] is None:
                    continue
                ph = estx.p_success(a["c"], a["k"], a["sev"], a["j"], a["q"])
                pi = estx.posterior_unresolved(1.0, ph, a["report"], a["verify"])
                nxt = [b["dispatch"] for b in r["attempts"] if b["dispatch"] > a["complete"]]
                if a["closed"] is None:
                    stop = nxt[0] if nxt else end
                    exposure[r["sev"]] += pi * max(0, stop - a["complete"]) / DAY
                elif a["callback"] is not None:
                    exposure[r["sev"]] += max(0, a["callback"] - a["complete"]) / DAY
                else:
                    stop = nxt[0] if nxt else end
                    T = max(0, stop - a["closed"]) / DAY
                    g = float(stats.gamma.cdf(T, shape, scale=scale))
                    pr = estx.p_report(a["sev"], bool(a["cu"])) * g
                    pi_end = pi * (1 - pr) / max(pi * (1 - pr) + (1 - pi), 1e-12)
                    exposure[r["sev"]] += (pi * (a["closed"] - a["complete"]) + pi_end * (stop - a["closed"])) / DAY
    nloss = defaultdict(int)
    amounts = defaultdict(list)
    for p in tr:
        for L in p["losses"]:
            nloss[L["sev"]] += 1
            amounts[L["sev"]].append(L["amount"])
    all_amt = [a for v in amounts.values() for a in v]
    hz = {s: (nloss[s] + 1.0) / (exposure[s] + 1000.0) for s in SEVS}
    mean_amt = {s: (float(np.mean(amounts[s])) if amounts[s] else (float(np.mean(all_amt)) if all_amt else 0.0)) for s in SEVS}
    report["severe_loss"] = {"events": dict(nloss), "exposure_expected_unresolved_days": dict(exposure)}

    # 7. termination GLM on contract-days
    Xk, yk = contract_day_rows(tr)
    Xkc, ykc = contract_day_rows(ca)
    best = None
    kgrid = []
    for a in ALPHA_GRID:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = PoissonRegressor(alpha=a, max_iter=1000).fit(Xk, yk)
        mu = np.clip(m.predict(Xkc), 1e-12, None)
        dev = float(2 * np.sum(np.where(ykc > 0, ykc * np.log(np.maximum(ykc, 1e-12) / mu), 0) - (ykc - mu)))
        kgrid.append({"alpha": a, "calib_deviance": dev})
        if best is None or dev < best[1]:
            best = (a, dev)
    assert best is not None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        km = PoissonRegressor(alpha=best[0], max_iter=1000).fit(Xk, yk)
    se = _poisson_se(km, Xk)
    term = {"intercept": float(km.intercept_), "coef": {f: float(v) for f, v in zip(("cb", "br", "sl", "oc"), km.coef_)},
            "se": {"intercept": se[0], **{f: se[i + 1] for i, f in enumerate(("cb", "br", "sl", "oc"))}},
            "alpha": best[0]}
    report["termination"] = {"contract_days": int(len(yk)), "events": int(yk.sum()), "grid": kgrid}

    # 8. info resample transition matrix, Dirichlet(1) shrinkage (DECISIONS: added model)
    cnt = {s: {t: 1.0 for t in SEVS} for s in SEVS}
    for p in tr:
        for b, a in p["infos"]:
            cnt[b][a] += 1.0
    trans = {s: {t: cnt[s][t] / sum(cnt[s].values()) for t in SEVS} for s in SEVS}
    report["info"] = {"n": int(sum(len(p["infos"]) for p in tr))}

    params = {
        "version": "estimator_v1",
        "success": succ,
        "report_verify": rv,
        "callback": {"p_report": p_report, "benign_rate": em["benign_rate"]},
        "report_delay": {"shape": float(shape), "scale_days": float(scale)},
        "lead_days": lead_days,
        "severe_loss": {"daily_hazard": hz, "mean_amount_dollars": mean_amt},
        "termination": term,
        "info": {"transition": trans},
    }
    return FrozenEstimator(params), {"report": report, "calib_success": (Xca, yca), "calib_callback": (Xcc, ycc)}


def train_and_freeze(cfg: Any, model_path: str, audit_path: str, n_train: int = 60, n_calib: int = 20,
                     workers: int = 4) -> dict[str, Any]:
    """Generate history (train, calib), fit M, freeze it to ``model_path`` and write the audit."""
    from marginbench.estimation.audit import audit_estimator
    from marginbench.estimation.history import generate_history
    from marginbench.hashing import write_json

    tr = generate_history(cfg, "train", n_train, workers)
    ca = generate_history(cfg, "calib", n_calib, workers)
    est, info = fit_estimator(tr, ca)
    est.params["provenance"] = {"train_portfolios": n_train, "calib_portfolios": n_calib,
                                "history_days": cfg.time.history_days, "config_hash": cfg.config_hash(),
                                "behavior_p0_prob": cfg.behavior.p0_prob,
                                "history_event_hashes": [d["event_hash"] for d in tr + ca]}
    digest = est.save(model_path)
    audit = audit_estimator(est, info, cfg)
    audit["estimator_hash"] = digest
    write_json(audit_path, audit)
    return {"estimator_hash": digest, "model_path": model_path, "audit_path": audit_path}
